#!/usr/bin/env python3
"""
Módulo para la gestión de pagos
Funciones para registrar, consultar y generar recibos de pagos
"""

import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from dateutil.relativedelta import relativedelta
import math

class PagoManager:
    """Modelo para la gestión de datos de pagos"""
    
    def __init__(self, db_path: str = '../database/prestamos.db'):
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtener conexión a la base de datos"""
        return sqlite3.connect(self.db_path)
    
    def obtener_pagos_pendientes(self, cliente_id: int = None) -> List[Dict]:
        """
        Obtener pagos pendientes por cliente o todos
        
        Args:
            cliente_id: ID del cliente (opcional)
        
        Returns:
            Lista de diccionarios con pagos pendientes
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT 
                        p.id as prestamo_id,
                        c.id as cliente_id,
                        c.nombre as nombre_cliente,
                        '' as apellido_cliente,
                        p.monto_total,
                        p.tasa_interes,
                        p.fecha_inicio,
                        p.plazo_quincenas,
                        p.estado,
                        COALESCE(SUM(pag.monto_capital + pag.monto_interes + pag.monto_seguro), 0) as total_pagado,
                        p.monto_total - COALESCE(SUM(pag.monto_capital + pag.monto_interes + pag.monto_seguro), 0) as saldo_pendiente
                    FROM prestamos p
                    JOIN clientes c ON p.cliente_id = c.id
                    LEFT JOIN pagos pag ON p.id = pag.prestamo_id
                    WHERE p.estado = 'ACTIVO'
                '''
                
                params = []
                if cliente_id:
                    query += " AND c.id = ?"
                    params.append(cliente_id)
                
                query += " GROUP BY p.id, c.id, c.nombre, p.monto_total, p.tasa_interes, p.fecha_inicio, p.plazo_quincenas, p.estado"
                query += " HAVING saldo_pendiente > 0"
                query += " ORDER BY c.nombre, p.fecha_inicio"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                pagos_pendientes = []
                for row in rows:
                    pagos_pendientes.append({
                        'prestamo_id': row[0],
                        'cliente_id': row[1],
                        'nombre_cliente': row[2],
                        'apellido_cliente': row[3],
                        'monto_total': row[4],
                        'tasa_interes': row[5],
                        'fecha_inicio': row[6],
                        'plazo_quincenas': row[7],
                        'estado': row[8],
                        'total_pagado': row[9],
                        'saldo_pendiente': row[10]
                    })
                
                return pagos_pendientes
        except sqlite3.Error as e:
            raise Exception(f"Error al obtener pagos pendientes: {e}")
    
    def registrar_pago(self, prestamo_id: int, fecha_pago: str, monto_capital: float, 
                      monto_interes: float, monto_seguro: float = 0, recibido_por: str = None) -> int:
        """
        Registrar un nuevo pago
        
        Args:
            prestamo_id: ID del préstamo
            fecha_pago: Fecha del pago (YYYY-MM-DD)
            monto_capital: Monto de capital
            monto_interes: Monto de interés
            monto_seguro: Monto de seguro (opcional)
            recibido_por: Nombre de quien recibió el pago
        
        Returns:
            ID del pago registrado
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Obtener información del préstamo
                cursor.execute('''
                    SELECT p.monto_total, p.plazo_quincenas, p.fecha_inicio,
                           COALESCE(SUM(pag.monto_capital + pag.monto_interes + pag.monto_seguro), 0) as total_pagado
                    FROM prestamos p
                    LEFT JOIN pagos pag ON p.id = pag.prestamo_id
                    WHERE p.id = ?
                    GROUP BY p.monto_total, p.plazo_quincenas, p.fecha_inicio
                ''', (prestamo_id,))
                
                prestamo_info = cursor.fetchone()
                if not prestamo_info:
                    raise Exception("Préstamo no encontrado")
                
                monto_total, plazo_quincenas, fecha_inicio, total_pagado = prestamo_info
                
                # Calcular número de quincena
                fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                fecha_pago_obj = datetime.strptime(fecha_pago, '%Y-%m-%d')
                
                # Calcular quincena basada en la fecha de inicio
                meses_transcurridos = (fecha_pago_obj.year - fecha_inicio_obj.year) * 12 + fecha_pago_obj.month - fecha_inicio_obj.month
                quincena = meses_transcurridos * 2 + 1
                if fecha_pago_obj.day > 15:
                    quincena += 1
                
                # Verificar que no se exceda el saldo pendiente
                saldo_pendiente = monto_total - total_pagado
                monto_total_pago = monto_capital + monto_interes + monto_seguro
                
                if monto_total_pago > saldo_pendiente:
                    raise Exception(f"El monto del pago (${monto_total_pago:,.2f}) excede el saldo pendiente (${saldo_pendiente:,.2f})")
                
                # Insertar el pago
                cursor.execute('''
                    INSERT INTO pagos (prestamo_id, numero_quincena, fecha_pago, monto_capital, 
                                     monto_interes, monto_seguro, recibido_por)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (prestamo_id, quincena, fecha_pago, monto_capital, monto_interes, monto_seguro, recibido_por))
                
                pago_id = cursor.lastrowid
                
                # Verificar si el préstamo está completamente pagado
                nuevo_total_pagado = total_pagado + monto_total_pago
                if nuevo_total_pagado >= monto_total:
                    cursor.execute('''
                        UPDATE prestamos SET estado = 'PAGADO' WHERE id = ?
                    ''', (prestamo_id,))
                
                conn.commit()
                return pago_id
                
        except sqlite3.Error as e:
            raise Exception(f"Error al registrar pago: {e}")
    
    def obtener_pago(self, pago_id: int) -> Optional[Dict]:
        """
        Obtener un pago por su ID
        
        Args:
            pago_id: ID del pago
        
        Returns:
            Dict con los datos del pago o None si no existe
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.id, p.prestamo_id, p.numero_quincena, p.fecha_pago,
                           p.monto_capital, p.monto_interes, p.monto_seguro, p.recibido_por,
                           pr.monto_total, c.nombre as nombre_cliente
                    FROM pagos p
                    JOIN prestamos pr ON p.prestamo_id = pr.id
                    JOIN clientes c ON pr.cliente_id = c.id
                    WHERE p.id = ?
                ''', (pago_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'prestamo_id': row[1],
                        'numero_quincena': row[2],
                        'fecha_pago': row[3],
                        'monto_capital': row[4],
                        'monto_interes': row[5],
                        'monto_seguro': row[6],
                        'recibido_por': row[7],
                        'monto_total_prestamo': row[8],
                        'nombre_cliente': row[9]
                    }
                return None
        except sqlite3.Error as e:
            raise Exception(f"Error al obtener pago: {e}")
    
    def listar_pagos(self, prestamo_id: int = None, cliente_id: int = None, 
                    fecha_inicio: str = None, fecha_fin: str = None) -> List[Dict]:
        """
        Listar pagos con filtros opcionales
        
        Args:
            prestamo_id: Filtrar por préstamo específico
            cliente_id: Filtrar por cliente específico
            fecha_inicio: Fecha de inicio para filtrar
            fecha_fin: Fecha de fin para filtrar
        
        Returns:
            Lista de diccionarios con los datos de los pagos
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT p.id, p.prestamo_id, p.numero_quincena, p.fecha_pago,
                           p.monto_capital, p.monto_interes, p.monto_seguro, p.recibido_por,
                           c.nombre as nombre_cliente, pr.monto_total as monto_prestamo
                    FROM pagos p
                    JOIN prestamos pr ON p.prestamo_id = pr.id
                    JOIN clientes c ON pr.cliente_id = c.id
                    WHERE 1=1
                '''
                
                params = []
                
                if prestamo_id:
                    query += " AND p.prestamo_id = ?"
                    params.append(prestamo_id)
                
                if cliente_id:
                    query += " AND pr.cliente_id = ?"
                    params.append(cliente_id)
                
                if fecha_inicio:
                    query += " AND p.fecha_pago >= ?"
                    params.append(fecha_inicio)
                
                if fecha_fin:
                    query += " AND p.fecha_pago <= ?"
                    params.append(fecha_fin)
                
                query += " ORDER BY p.fecha_pago DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                pagos = []
                for row in rows:
                    pagos.append({
                        'id': row[0],
                        'prestamo_id': row[1],
                        'numero_quincena': row[2],
                        'fecha_pago': row[3],
                        'monto_capital': row[4],
                        'monto_interes': row[5],
                        'monto_seguro': row[6],
                        'recibido_por': row[7],
                        'nombre_cliente': row[8],
                        'monto_prestamo': row[9],
                        'monto_total': row[4] + row[5] + row[6]
                    })
                
                return pagos
        except sqlite3.Error as e:
            raise Exception(f"Error al listar pagos: {e}")
    
    def calcular_saldo_pendiente(self, prestamo_id: int) -> float:
        """
        Calcular el saldo pendiente de un préstamo
        
        Args:
            prestamo_id: ID del préstamo
        
        Returns:
            float: Saldo pendiente
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.monto_total,
                           COALESCE(SUM(pag.monto_capital + pag.monto_interes + pag.monto_seguro), 0) as total_pagado
                    FROM prestamos p
                    LEFT JOIN pagos pag ON p.id = pag.prestamo_id
                    WHERE p.id = ?
                    GROUP BY p.monto_total
                ''', (prestamo_id,))
                
                row = cursor.fetchone()
                if row:
                    monto_total, total_pagado = row
                    return max(0, monto_total - total_pagado)
                return 0
        except sqlite3.Error as e:
            raise Exception(f"Error al calcular saldo pendiente: {e}")
    
    def obtener_historial_pagos(self, prestamo_id: int) -> List[Dict]:
        """
        Obtener historial completo de pagos de un préstamo
        
        Args:
            prestamo_id: ID del préstamo
        
        Returns:
            Lista de diccionarios con el historial de pagos
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.id, p.numero_quincena, p.fecha_pago, p.monto_capital,
                           p.monto_interes, p.monto_seguro, p.recibido_por,
                           (p.monto_capital + p.monto_interes + p.monto_seguro) as monto_total
                    FROM pagos p
                    WHERE p.prestamo_id = ?
                    ORDER BY p.fecha_pago
                ''', (prestamo_id,))
                
                rows = cursor.fetchall()
                historial = []
                
                for row in rows:
                    historial.append({
                        'id': row[0],
                        'numero_quincena': row[1],
                        'fecha_pago': row[2],
                        'monto_capital': row[3],
                        'monto_interes': row[4],
                        'monto_seguro': row[5],
                        'recibido_por': row[6],
                        'monto_total': row[7]
                    })
                
                return historial
        except sqlite3.Error as e:
            raise Exception(f"Error al obtener historial de pagos: {e}")
    
    def verificar_pago_completo(self, prestamo_id: int) -> bool:
        """
        Verificar si un préstamo está completamente pagado
        
        Args:
            prestamo_id: ID del préstamo
        
        Returns:
            bool: True si está completamente pagado
        """
        try:
            saldo_pendiente = self.calcular_saldo_pendiente(prestamo_id)
            return saldo_pendiente <= 0
        except Exception as e:
            raise Exception(f"Error al verificar pago completo: {e}")

# Funciones de conveniencia
def registrar_pago(prestamo_id: int, fecha_pago: str, monto_capital: float, 
                  monto_interes: float, monto_seguro: float = 0, recibido_por: str = None) -> int:
    """Función de conveniencia para registrar un pago"""
    manager = PagoManager()
    return manager.registrar_pago(prestamo_id, fecha_pago, monto_capital, monto_interes, monto_seguro, recibido_por)

def obtener_pagos_pendientes(cliente_id: int = None) -> List[Dict]:
    """Función de conveniencia para obtener pagos pendientes"""
    manager = PagoManager()
    return manager.obtener_pagos_pendientes(cliente_id)

def calcular_saldo_pendiente(prestamo_id: int) -> float:
    """Función de conveniencia para calcular saldo pendiente"""
    manager = PagoManager()
    return manager.calcular_saldo_pendiente(prestamo_id)

# ============================================================================
# INTERFAZ GRÁFICA - PAGOSWINDOW
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date
import math

class PagoDialog:
    """Diálogo para registrar pagos"""
    
    def __init__(self, parent, prestamo_data: Dict):
        self.parent = parent
        self.prestamo_data = prestamo_data
        self.result = None
        
        # Crear ventana de diálogo
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Registrar Pago - Préstamo #{prestamo_data['prestamo_id']}")
        self.dialog.geometry("500x500")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrar diálogo
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.crear_widgets()
        self.cargar_datos_prestamo()
    
    def crear_widgets(self):
        """Crear widgets del diálogo"""
        # Frame principal
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Título
        ttk.Label(main_frame, text="Registrar Pago", font=('Arial', 14, 'bold')).pack(pady=(0, 20))
        
        # Información del préstamo
        info_frame = ttk.LabelFrame(main_frame, text="Información del Préstamo", padding="10")
        info_frame.pack(fill='x', pady=(0, 20))
        
        self.info_label = ttk.Label(info_frame, text="", font=('Arial', 10))
        self.info_label.pack()
        
        # Frame para formulario
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill='x', pady=10)
        
        # Fecha de pago
        ttk.Label(form_frame, text="Fecha de Pago *:").grid(row=0, column=0, sticky='w', pady=5)
        self.fecha_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        self.fecha_entry = ttk.Entry(form_frame, textvariable=self.fecha_var, width=30)
        self.fecha_entry.grid(row=0, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Monto capital
        ttk.Label(form_frame, text="Monto Capital *:").grid(row=1, column=0, sticky='w', pady=5)
        self.capital_var = tk.StringVar()
        self.capital_entry = ttk.Entry(form_frame, textvariable=self.capital_var, width=30)
        self.capital_entry.grid(row=1, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Monto interés
        ttk.Label(form_frame, text="Monto Interés:").grid(row=2, column=0, sticky='w', pady=5)
        self.interes_var = tk.StringVar(value="0")
        self.interes_entry = ttk.Entry(form_frame, textvariable=self.interes_var, width=30)
        self.interes_entry.grid(row=2, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Monto seguro
        ttk.Label(form_frame, text="Monto Seguro:").grid(row=3, column=0, sticky='w', pady=5)
        self.seguro_var = tk.StringVar(value="0")
        self.seguro_entry = ttk.Entry(form_frame, textvariable=self.seguro_var, width=30)
        self.seguro_entry.grid(row=3, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Recibido por
        ttk.Label(form_frame, text="Recibido por:").grid(row=4, column=0, sticky='w', pady=5)
        self.recibido_var = tk.StringVar()
        self.recibido_entry = ttk.Entry(form_frame, textvariable=self.recibido_var, width=30)
        self.recibido_entry.grid(row=4, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Configurar expansión de columnas
        form_frame.columnconfigure(1, weight=1)
        
        # Frame para resumen
        resumen_frame = ttk.LabelFrame(main_frame, text="Resumen del Pago", padding="10")
        resumen_frame.pack(fill='x', pady=10)
        
        self.resumen_label = ttk.Label(resumen_frame, text="", font=('Arial', 10))
        self.resumen_label.pack()
        
        # Frame para botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(20, 0))
        
        # Botones
        ttk.Button(button_frame, text="Calcular", command=self.calcular_resumen).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="Guardar", command=self.guardar).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Cancelar", command=self.cancelar).pack(side='right')
        
        # Enfocar en el primer campo
        self.fecha_entry.focus()
        
        # Bind eventos
        self.capital_var.trace('w', lambda *args: self.calcular_resumen())
        self.interes_var.trace('w', lambda *args: self.calcular_resumen())
        self.seguro_var.trace('w', lambda *args: self.calcular_resumen())
        self.dialog.bind('<Return>', lambda e: self.guardar())
        self.dialog.bind('<Escape>', lambda e: self.cancelar())
    
    def cargar_datos_prestamo(self):
        """Cargar información del préstamo"""
        prestamo = self.prestamo_data
        info_text = f"""Cliente: {prestamo['nombre_cliente']}
Monto Total: ${prestamo['monto_total']:,.2f}
Saldo Pendiente: ${prestamo['saldo_pendiente']:,.2f}
Tasa de Interés: {prestamo['tasa_interes']}%
Fecha de Inicio: {prestamo['fecha_inicio']}"""
        
        self.info_label.config(text=info_text)
        self.calcular_resumen()
    
    def calcular_resumen(self):
        """Calcular resumen del pago"""
        try:
            capital = float(self.capital_var.get() or 0)
            interes = float(self.interes_var.get() or 0)
            seguro = float(self.seguro_var.get() or 0)
            total = capital + interes + seguro
            
            saldo_pendiente = self.prestamo_data['saldo_pendiente']
            
            resumen_text = f"""Monto Capital: ${capital:,.2f}
Monto Interés: ${interes:,.2f}
Monto Seguro: ${seguro:,.2f}
Total a Pagar: ${total:,.2f}
Saldo Restante: ${max(0, saldo_pendiente - total):,.2f}"""
            
            self.resumen_label.config(text=resumen_text)
            
        except ValueError:
            self.resumen_label.config(text="Ingresa montos válidos")
    
    def guardar(self):
        """Guardar datos del pago"""
        if not self.validar_datos():
            return
        
        try:
            fecha = self.fecha_var.get()
            capital = float(self.capital_var.get())
            interes = float(self.interes_var.get() or 0)
            seguro = float(self.seguro_var.get() or 0)
            recibido = self.recibido_var.get()
            
            self.result = {
                'prestamo_id': self.prestamo_data['prestamo_id'],
                'fecha_pago': fecha,
                'monto_capital': capital,
                'monto_interes': interes,
                'monto_seguro': seguro,
                'recibido_por': recibido
            }
            
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Dato inválido: {e}", parent=self.dialog)
    
    def validar_datos(self):
        """Validar datos del formulario"""
        # Validar fecha
        fecha = self.fecha_var.get()
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
            fecha_actual = datetime.now()
            if fecha_obj > fecha_actual:
                messagebox.showerror("Error", "La fecha de pago no puede ser futura", parent=self.dialog)
                self.fecha_entry.focus()
                return False
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido (YYYY-MM-DD)", parent=self.dialog)
            self.fecha_entry.focus()
            return False
        
        # Validar monto capital
        try:
            capital = float(self.capital_var.get())
            if capital <= 0:
                messagebox.showerror("Error", "El monto de capital debe ser mayor a 0", parent=self.dialog)
                self.capital_entry.focus()
                return False
        except ValueError:
            messagebox.showerror("Error", "El monto de capital debe ser un número válido", parent=self.dialog)
            self.capital_entry.focus()
            return False
        
        # Validar montos adicionales
        try:
            interes = float(self.interes_var.get() or 0)
            seguro = float(self.seguro_var.get() or 0)
            if interes < 0 or seguro < 0:
                messagebox.showerror("Error", "Los montos de interés y seguro no pueden ser negativos", parent=self.dialog)
                return False
        except ValueError:
            messagebox.showerror("Error", "Los montos deben ser números válidos", parent=self.dialog)
            return False
        
        # Validar que no exceda el saldo pendiente
        total_pago = capital + interes + seguro
        saldo_pendiente = self.prestamo_data['saldo_pendiente']
        
        if total_pago > saldo_pendiente:
            messagebox.showerror("Error", f"El total del pago (${total_pago:,.2f}) excede el saldo pendiente (${saldo_pendiente:,.2f})", parent=self.dialog)
            return False
        
        return True
    
    def cancelar(self):
        """Cancelar operación"""
        self.result = None
        self.dialog.destroy()

class PagosWindow(ttk.Frame):
    """Ventana principal de gestión de pagos"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # Inicializar modelo y controlador
        self.model = PagoManager()
        self.controller = PagoController(self.model)
        
        # Variables
        self.pago_seleccionado = None
        self.clientes_data = []
        
        # Crear interfaz
        self.cargar_clientes()
        self.crear_widgets()
        self.listar_pagos_pendientes()
    
    def cargar_clientes(self):
        """Cargar lista de clientes para el combobox"""
        try:
            from src.clientes import ClienteModel
            cliente_model = ClienteModel()
            clientes = cliente_model.listar_clientes()
            self.clientes_data = [(c[0], c[1]) for c in clientes]  # (id, nombre)
        except Exception as e:
            print(f"Error al cargar clientes: {e}")
            self.clientes_data = []
    
    def crear_widgets(self):
        """Crear widgets de la interfaz"""
        # Frame principal
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Título
        ttk.Label(main_frame, text="Gestión de Pagos", font=('Arial', 16, 'bold')).pack(pady=(0, 20))
        
        # Frame superior para filtros y botones
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill='x', pady=(0, 10))
        
        # Filtros
        filter_frame = ttk.LabelFrame(top_frame, text="Filtros", padding="10")
        filter_frame.pack(side='left', fill='x', expand=True)
        
        # Primera fila de filtros
        filter_row1 = ttk.Frame(filter_frame)
        filter_row1.pack(fill='x', pady=(0, 5))
        
        ttk.Label(filter_row1, text="Buscar por:").pack(side='left', padx=(0, 5))
        self.tipo_busqueda = tk.StringVar(value="cliente")
        ttk.Radiobutton(filter_row1, text="Cliente", variable=self.tipo_busqueda, value="cliente").pack(side='left', padx=(0, 10))
        ttk.Radiobutton(filter_row1, text="Fecha", variable=self.tipo_busqueda, value="fecha").pack(side='left', padx=(0, 10))
        ttk.Radiobutton(filter_row1, text="Monto", variable=self.tipo_busqueda, value="monto").pack(side='left')
        
        # Segunda fila de filtros
        filter_row2 = ttk.Frame(filter_frame)
        filter_row2.pack(fill='x')
        
        ttk.Label(filter_row2, text="Término:").pack(side='left', padx=(0, 5))
        self.buscar_var = tk.StringVar()
        self.buscar_entry = ttk.Entry(filter_row2, textvariable=self.buscar_var, width=30)
        self.buscar_entry.pack(side='left', padx=(0, 10))
        
        ttk.Label(filter_row2, text="Cliente:").pack(side='left', padx=(0, 5))
        self.cliente_var = tk.StringVar(value="TODOS")
        cliente_combo = ttk.Combobox(filter_row2, textvariable=self.cliente_var, 
                                    values=["TODOS"] + [f"{c[0]} - {c[1]}" for c in self.clientes_data], 
                                    width=20, state='readonly')
        cliente_combo.pack(side='left', padx=(0, 10))
        
        ttk.Button(filter_row2, text="🔍 Buscar", command=self.buscar_pagos).pack(side='left', padx=(0, 5))
        ttk.Button(filter_row2, text="🔄 Limpiar", command=self.limpiar_filtros).pack(side='left')
        
        # Botones principales
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side='right')
        
        ttk.Button(button_frame, text="Registrar Pago", command=self.registrar_pago).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Ver Historial", command=self.ver_historial).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Generar Recibo", command=self.generar_recibo).pack(side='left', padx=5)
        
        # Frame para la tabla
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill='both', expand=True)
        
        # Crear Treeview
        columns = ('Préstamo ID', 'Cliente', 'Monto Total', 'Pagado', 'Saldo', 'Estado')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Configurar columnas
        self.tree.heading('Préstamo ID', text='Préstamo ID')
        self.tree.heading('Cliente', text='Cliente')
        self.tree.heading('Monto Total', text='Monto Total')
        self.tree.heading('Pagado', text='Pagado')
        self.tree.heading('Saldo', text='Saldo Pendiente')
        self.tree.heading('Estado', text='Estado')
        
        self.tree.column('Préstamo ID', width=100, anchor='center')
        self.tree.column('Cliente', width=200)
        self.tree.column('Monto Total', width=120, anchor='e')
        self.tree.column('Pagado', width=120, anchor='e')
        self.tree.column('Saldo', width=120, anchor='e')
        self.tree.column('Estado', width=100, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Empaquetar tabla y scrollbar
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind eventos
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        self.tree.bind('<Double-1>', lambda e: self.registrar_pago())
    
    def listar_pagos_pendientes(self):
        """Listar pagos pendientes en la tabla"""
        try:
            # Limpiar tabla
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Obtener pagos pendientes
            pagos_pendientes = self.controller.obtener_pagos_pendientes()
            
            # Insertar en tabla
            for pago in pagos_pendientes:
                self.tree.insert('', 'end', values=(
                    pago['prestamo_id'],
                    pago['nombre_cliente'],
                    f"${pago['monto_total']:,.2f}",
                    f"${pago['total_pagado']:,.2f}",
                    f"${pago['saldo_pendiente']:,.2f}",
                    pago['estado']
                ))
            
            # Actualizar estado
            self.actualizar_estado()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al listar pagos pendientes: {e}")
    
    def buscar_pagos(self):
        """Buscar pagos por término y tipo"""
        try:
            termino = self.buscar_var.get().strip()
            tipo = self.tipo_busqueda.get()
            cliente = self.cliente_var.get()
            
            if not termino and cliente == "TODOS":
                self.listar_pagos_pendientes()
                return
            
            # Limpiar tabla
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Obtener pagos filtrados
            pagos = self.controller.buscar_pagos_avanzado(termino, tipo, cliente)
            
            # Insertar en tabla
            for pago in pagos:
                self.tree.insert('', 'end', values=(
                    pago['prestamo_id'],
                    pago['nombre_cliente'],
                    f"${pago['monto_total']:,.2f}",
                    f"${pago['total_pagado']:,.2f}",
                    f"${pago['saldo_pendiente']:,.2f}",
                    pago['estado']
                ))
            
            # Mostrar resultado de búsqueda
            if termino:
                if pagos:
                    messagebox.showinfo("Búsqueda", f"Se encontraron {len(pagos)} pago(s) con '{termino}' en {tipo}")
                else:
                    messagebox.showinfo("Búsqueda", f"No se encontraron pagos con '{termino}' en {tipo}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar pagos: {e}")
    
    def limpiar_filtros(self):
        """Limpiar filtros y mostrar todos los pagos pendientes"""
        self.buscar_var.set("")
        self.cliente_var.set("TODOS")
        self.listar_pagos_pendientes()
    
    def registrar_pago(self):
        """Abrir diálogo para registrar pago"""
        if not self.pago_seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un préstamo para registrar pago")
            return
        
        try:
            prestamo_id = self.pago_seleccionado[0]
            prestamo_data = self.controller.obtener_prestamo_para_pago(prestamo_id)
            
            if prestamo_data:
                dialog = PagoDialog(self, prestamo_data)
                self.wait_window(dialog.dialog)
                
                if dialog.result:
                    datos = dialog.result
                    self.controller.registrar_pago(
                        datos['prestamo_id'],
                        datos['fecha_pago'],
                        datos['monto_capital'],
                        datos['monto_interes'],
                        datos['monto_seguro'],
                        datos['recibido_por']
                    )
                    messagebox.showinfo("Éxito", "Pago registrado correctamente")
                    self.listar_pagos_pendientes()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al registrar pago: {e}")
    
    def ver_historial(self):
        """Ver historial de pagos del préstamo seleccionado"""
        if not self.pago_seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un préstamo para ver historial")
            return
        
        try:
            prestamo_id = self.pago_seleccionado[0]
            historial = self.controller.obtener_historial_pagos(prestamo_id)
            
            if historial:
                self.mostrar_historial_pagos(prestamo_id, historial)
            else:
                messagebox.showinfo("Información", "No hay pagos registrados para este préstamo")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error al obtener historial: {e}")
    
    def mostrar_historial_pagos(self, prestamo_id: int, historial: List[Dict]):
        """Mostrar ventana de historial de pagos"""
        try:
            # Crear ventana de historial
            hist_window = tk.Toplevel(self)
            hist_window.title(f"Historial de Pagos - Préstamo #{prestamo_id}")
            hist_window.geometry("800x500")
            
            # Frame principal
            main_frame = ttk.Frame(hist_window, padding="20")
            main_frame.pack(fill='both', expand=True)
            
            # Título
            ttk.Label(main_frame, text=f"Historial de Pagos - Préstamo #{prestamo_id}", 
                     font=('Arial', 14, 'bold')).pack(pady=(0, 20))
            
            # Crear Treeview para historial
            columns = ('ID', 'Quincena', 'Fecha', 'Capital', 'Interés', 'Seguro', 'Total', 'Recibido por')
            tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=15)
            
            tree.heading('ID', text='ID')
            tree.heading('Quincena', text='Quincena')
            tree.heading('Fecha', text='Fecha')
            tree.heading('Capital', text='Capital')
            tree.heading('Interés', text='Interés')
            tree.heading('Seguro', text='Seguro')
            tree.heading('Total', text='Total')
            tree.heading('Recibido por', text='Recibido por')
            
            tree.column('ID', width=50, anchor='center')
            tree.column('Quincena', width=80, anchor='center')
            tree.column('Fecha', width=100, anchor='center')
            tree.column('Capital', width=100, anchor='e')
            tree.column('Interés', width=100, anchor='e')
            tree.column('Seguro', width=100, anchor='e')
            tree.column('Total', width=100, anchor='e')
            tree.column('Recibido por', width=150)
            
            # Cargar datos
            for pago in historial:
                tree.insert('', 'end', values=(
                    pago['id'],
                    pago['numero_quincena'],
                    pago['fecha_pago'],
                    f"${pago['monto_capital']:,.2f}",
                    f"${pago['monto_interes']:,.2f}",
                    f"${pago['monto_seguro']:,.2f}",
                    f"${pago['monto_total']:,.2f}",
                    pago['recibido_por'] or ''
                ))
            
            tree.pack(fill='both', expand=True, pady=10)
            
            # Botón cerrar
            ttk.Button(main_frame, text="Cerrar", command=hist_window.destroy).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al mostrar historial: {e}")
    
    def generar_recibo(self):
        """Generar recibo del pago seleccionado"""
        if not self.pago_seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un préstamo para generar recibo")
            return
        
        try:
            prestamo_id = self.pago_seleccionado[0]
            # TODO: Implementar generación de recibo
            messagebox.showinfo("Información", "Generación de recibos en desarrollo")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar recibo: {e}")
    
    def on_select(self, event):
        """Manejar selección de pago"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            self.pago_seleccionado = item['values']
        else:
            self.pago_seleccionado = None
        
        self.actualizar_estado()
    
    def actualizar_estado(self):
        """Actualizar estado de botones según selección"""
        tiene_seleccion = self.pago_seleccionado is not None
        
        # Habilitar/deshabilitar botones según contexto
        for child in self.winfo_children():
            if isinstance(child, ttk.Frame):
                for button in child.winfo_children():
                    if isinstance(button, ttk.Frame):
                        for btn in button.winfo_children():
                            if isinstance(btn, ttk.Button):
                                if "Registrar Pago" in btn['text'] or "Ver Historial" in btn['text'] or "Generar Recibo" in btn['text']:
                                    btn['state'] = 'normal' if tiene_seleccion else 'disabled'

class PagoController:
    """Controlador para la lógica de negocio de pagos"""
    
    def __init__(self, model: PagoManager):
        self.model = model
    
    def obtener_pagos_pendientes(self) -> List[Dict]:
        """Obtener lista de pagos pendientes"""
        return self.model.obtener_pagos_pendientes()
    
    def buscar_pagos_avanzado(self, termino: str, tipo: str, cliente: str) -> List[Dict]:
        """Buscar pagos por término, tipo y cliente"""
        # TODO: Implementar búsqueda avanzada
        return self.model.obtener_pagos_pendientes()
    
    def obtener_prestamo_para_pago(self, prestamo_id: int) -> Optional[Dict]:
        """Obtener información del préstamo para pago"""
        try:
            pagos_pendientes = self.model.obtener_pagos_pendientes()
            for pago in pagos_pendientes:
                if pago['prestamo_id'] == prestamo_id:
                    return pago
            return None
        except Exception as e:
            raise Exception(f"Error al obtener préstamo: {e}")
    
    def registrar_pago(self, prestamo_id: int, fecha_pago: str, monto_capital: float, 
                      monto_interes: float, monto_seguro: float, recibido_por: str) -> int:
        """Registrar nuevo pago con validaciones"""
        if monto_capital <= 0:
            raise ValueError("El monto de capital debe ser mayor a 0")
        
        if monto_interes < 0 or monto_seguro < 0:
            raise ValueError("Los montos de interés y seguro no pueden ser negativos")
        
        return self.model.registrar_pago(prestamo_id, fecha_pago, monto_capital, monto_interes, monto_seguro, recibido_por)
    
    def obtener_historial_pagos(self, prestamo_id: int) -> List[Dict]:
        """Obtener historial de pagos de un préstamo"""
        return self.model.obtener_historial_pagos(prestamo_id)
