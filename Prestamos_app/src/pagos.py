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
import os
import subprocess
import platform
from src.tarifas import obtener_cuota_quincenal, calcular_total_pagar

def get_db_path():
    """Obtener la ruta absoluta de la base de datos"""
    # Obtener el directorio base del proyecto (un nivel arriba de src)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_dir = os.path.join(base_dir, 'database')
    db_path = os.path.join(db_dir, 'prestamos.db')
    return db_path

class PagoManager:
    """Modelo para la gestión de datos de pagos"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = get_db_path()
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
                
                # Verificar si los campos nuevos existen
                cursor.execute("PRAGMA table_info(prestamos)")
                columnas = cursor.fetchall()
                nombres_columnas = [col[1] for col in columnas]
                
                if 'tiene_seguro' in nombres_columnas:
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
                            p.tiene_seguro,
                            COALESCE(SUM(pag.monto_capital + pag.monto_interes + pag.monto_seguro), 0) as total_pagado,
                            COUNT(pag.id) as pagos_realizados
                        FROM prestamos p
                        JOIN clientes c ON p.cliente_id = c.id
                        LEFT JOIN pagos pag ON p.id = pag.prestamo_id
                        WHERE p.estado = 'ACTIVO'
                    '''
                    query_group = " GROUP BY p.id, c.id, c.nombre, p.monto_total, p.tasa_interes, p.fecha_inicio, p.plazo_quincenas, p.estado, p.tiene_seguro"
                else:
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
                            0 as tiene_seguro,
                            COALESCE(SUM(pag.monto_capital + pag.monto_interes + pag.monto_seguro), 0) as total_pagado,
                            COUNT(pag.id) as pagos_realizados
                        FROM prestamos p
                        JOIN clientes c ON p.cliente_id = c.id
                        LEFT JOIN pagos pag ON p.id = pag.prestamo_id
                        WHERE p.estado = 'ACTIVO'
                    '''
                    query_group = " GROUP BY p.id, c.id, c.nombre, p.monto_total, p.tasa_interes, p.fecha_inicio, p.plazo_quincenas, p.estado"
                
                params = []
                if cliente_id:
                    query += " AND c.id = ?"
                    params.append(cliente_id)
                
                query += query_group
                query += " ORDER BY c.nombre, p.fecha_inicio"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                pagos_pendientes = []
                for row in rows:
                    prestamo_id = row[0]
                    cliente_id = row[1]
                    nombre_cliente = row[2]
                    apellido_cliente = row[3]
                    monto_prestamo = row[4]  # Monto original del préstamo
                    tasa_interes = row[5]
                    fecha_inicio = row[6]
                    plazo_quincenas = row[7]
                    estado = row[8]
                    tiene_seguro = bool(row[9]) if len(row) > 9 else False
                    total_pagado = row[10]
                    pagos_realizados = row[11]  # Número de pagos realizados
                    
                    # Calcular cuota quincenal y total a pagar usando la matriz de tarifas
                    cuota_base = obtener_cuota_quincenal(monto_prestamo, plazo_quincenas)
                    cuota_quincenal = cuota_base + (15.0 if tiene_seguro else 0.0)
                    total_base = calcular_total_pagar(monto_prestamo, plazo_quincenas)
                    total_a_pagar = total_base + (15.0 * plazo_quincenas if tiene_seguro else 0.0)
                    
                    # Calcular saldo pendiente: total a pagar - total pagado
                    saldo_pendiente = total_a_pagar - total_pagado
                    
                    # Calcular progreso (ej: 1/8, 2/8, etc.)
                    # El siguiente pago será pagos_realizados + 1
                    siguiente_pago = pagos_realizados + 1
                    progreso = f"{siguiente_pago}/{plazo_quincenas}"
                    
                    # Solo incluir si hay saldo pendiente
                    if saldo_pendiente > 0:
                        pagos_pendientes.append({
                            'prestamo_id': prestamo_id,
                            'cliente_id': cliente_id,
                            'nombre_cliente': nombre_cliente,
                            'apellido_cliente': apellido_cliente,
                            'monto_prestamo': monto_prestamo,  # Monto original
                            'monto_total': monto_prestamo,  # Mantener para compatibilidad
                            'tasa_interes': tasa_interes,
                            'fecha_inicio': fecha_inicio,
                            'plazo_quincenas': plazo_quincenas,
                            'estado': estado,
                            'total_pagado': total_pagado,
                            'saldo_pendiente': max(0, saldo_pendiente),  # Asegurar que no sea negativo
                            'cuota_quincenal': cuota_quincenal,
                            'total_a_pagar': total_a_pagar,
                            'progreso': progreso,
                            'pagos_realizados': pagos_realizados
                        })
                
                return pagos_pendientes
        except sqlite3.Error as e:
            raise Exception(f"Error al obtener pagos pendientes: {e}")
    
    def registrar_pago(self, prestamo_id: int, fecha_pago: str, monto_pago: float, 
                      recibido_por: str = None) -> int:
        """
        Registrar un nuevo pago de quincena
        
        Args:
            prestamo_id: ID del préstamo
            fecha_pago: Fecha del pago (YYYY-MM-DD)
            monto_pago: Monto del pago (debe ser igual a la cuota quincenal)
            recibido_por: Nombre de quien recibió el pago
        
        Returns:
            ID del pago registrado
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar si los campos nuevos existen
                cursor.execute("PRAGMA table_info(prestamos)")
                columnas = cursor.fetchall()
                nombres_columnas = [col[1] for col in columnas]
                
                if 'tiene_seguro' in nombres_columnas:
                    query_prestamo = '''
                        SELECT p.monto_total, p.plazo_quincenas, p.fecha_inicio, p.tiene_seguro,
                               COALESCE(SUM(pag.monto_capital + pag.monto_interes + pag.monto_seguro), 0) as total_pagado
                        FROM prestamos p
                        LEFT JOIN pagos pag ON p.id = pag.prestamo_id
                        WHERE p.id = ?
                        GROUP BY p.monto_total, p.plazo_quincenas, p.fecha_inicio, p.tiene_seguro
                    '''
                else:
                    query_prestamo = '''
                        SELECT p.monto_total, p.plazo_quincenas, p.fecha_inicio, 0,
                               COALESCE(SUM(pag.monto_capital + pag.monto_interes + pag.monto_seguro), 0) as total_pagado
                        FROM prestamos p
                        LEFT JOIN pagos pag ON p.id = pag.prestamo_id
                        WHERE p.id = ?
                        GROUP BY p.monto_total, p.plazo_quincenas, p.fecha_inicio
                    '''
                
                cursor.execute(query_prestamo, (prestamo_id,))
                prestamo_info = cursor.fetchone()
                if not prestamo_info:
                    raise Exception("Préstamo no encontrado")
                
                if len(prestamo_info) >= 5:
                    monto_prestamo, plazo_quincenas, fecha_inicio, tiene_seguro, total_pagado = prestamo_info[:5]
                    tiene_seguro = bool(tiene_seguro)
                else:
                    monto_prestamo, plazo_quincenas, fecha_inicio, total_pagado = prestamo_info[:4]
                    tiene_seguro = False
                
                # Calcular cuota quincenal y total a pagar usando la matriz de tarifas
                cuota_base = obtener_cuota_quincenal(monto_prestamo, plazo_quincenas)
                cuota_quincenal = cuota_base + (15.0 if tiene_seguro else 0.0)
                total_base = calcular_total_pagar(monto_prestamo, plazo_quincenas)
                total_a_pagar = total_base + (15.0 * plazo_quincenas if tiene_seguro else 0.0)
                
                # Validar que el monto del pago sea exactamente la cuota quincenal
                if abs(monto_pago - cuota_quincenal) > 0.01:  # Permitir pequeña diferencia por redondeo
                    raise Exception(f"El monto del pago (${monto_pago:,.2f}) debe ser exactamente la cuota quincenal (${cuota_quincenal:,.2f})")
                
                # Obtener el número de la próxima quincena
                numero_quincena = self.obtener_proxima_quincena(prestamo_id)
                
                # Verificar que no se exceda el número de quincenas
                if numero_quincena > plazo_quincenas:
                    raise Exception(f"Ya se han registrado todos los pagos. El préstamo tiene {plazo_quincenas} quincenas.")
                
                # Verificar que no se exceda el saldo pendiente
                saldo_pendiente = total_a_pagar - total_pagado
                if monto_pago > saldo_pendiente:
                    raise Exception(f"El monto del pago (${monto_pago:,.2f}) excede el saldo pendiente (${saldo_pendiente:,.2f})")
                
                # El monto del pago se registra como capital (ya incluye intereses en la tarifa)
                # Para mantener compatibilidad con la estructura de la BD, registramos:
                # - monto_capital = cuota quincenal (todo el pago)
                # - monto_interes = 0 (ya está incluido en la tarifa)
                # - monto_seguro = 0
                cursor.execute('''
                    INSERT INTO pagos (prestamo_id, numero_quincena, fecha_pago, monto_capital, 
                                     monto_interes, monto_seguro, recibido_por)
                    VALUES (?, ?, ?, ?, 0, 0, ?)
                ''', (prestamo_id, numero_quincena, fecha_pago, monto_pago, recibido_por))
                
                pago_id = cursor.lastrowid
                
                # Verificar si el préstamo está completamente pagado
                nuevo_total_pagado = total_pagado + monto_pago
                if nuevo_total_pagado >= total_a_pagar or numero_quincena >= plazo_quincenas:
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
            float: Saldo pendiente (total a pagar - total pagado)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.monto_total, p.plazo_quincenas,
                           COALESCE(SUM(pag.monto_capital + pag.monto_interes + pag.monto_seguro), 0) as total_pagado
                    FROM prestamos p
                    LEFT JOIN pagos pag ON p.id = pag.prestamo_id
                    WHERE p.id = ?
                    GROUP BY p.monto_total, p.plazo_quincenas
                ''', (prestamo_id,))
                
                row = cursor.fetchone()
                if row:
                    monto_prestamo, plazo_quincenas, total_pagado = row
                    # Calcular total a pagar usando la matriz de tarifas
                    total_a_pagar = calcular_total_pagar(monto_prestamo, plazo_quincenas)
                    return max(0, total_a_pagar - total_pagado)
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
                    ORDER BY p.numero_quincena
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
    
    def obtener_proxima_quincena(self, prestamo_id: int) -> int:
        """
        Obtener el número de la próxima quincena a pagar
        
        Args:
            prestamo_id: ID del préstamo
        
        Returns:
            int: Número de la próxima quincena (1, 2, 3, etc.)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COALESCE(MAX(numero_quincena), 0) + 1
                    FROM pagos
                    WHERE prestamo_id = ?
                ''', (prestamo_id,))
                
                row = cursor.fetchone()
                return row[0] if row else 1
        except sqlite3.Error as e:
            raise Exception(f"Error al obtener próxima quincena: {e}")
    
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
def registrar_pago(prestamo_id: int, fecha_pago: str, monto_pago: float, 
                  recibido_por: str = None) -> int:
    """Función de conveniencia para registrar un pago"""
    manager = PagoManager()
    return manager.registrar_pago(prestamo_id, fecha_pago, monto_pago, recibido_por)

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
    
    def __init__(self, parent, prestamo_data: Dict, pago_manager: PagoManager):
        self.parent = parent
        self.prestamo_data = prestamo_data
        self.pago_manager = pago_manager
        self.result = None
        
        # Obtener próxima quincena
        self.proxima_quincena = self.pago_manager.obtener_proxima_quincena(prestamo_data['prestamo_id'])
        
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
        
        # Monto del pago (cuota quincenal)
        ttk.Label(form_frame, text="Monto a Pagar *:").grid(row=1, column=0, sticky='w', pady=5)
        self.monto_var = tk.StringVar()
        self.monto_entry = ttk.Entry(form_frame, textvariable=self.monto_var, width=30)
        self.monto_entry.grid(row=1, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Recibido por
        ttk.Label(form_frame, text="Recibido por:").grid(row=2, column=0, sticky='w', pady=5)
        self.recibido_var = tk.StringVar()
        self.recibido_entry = ttk.Entry(form_frame, textvariable=self.recibido_var, width=30)
        self.recibido_entry.grid(row=2, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Configurar expansión de columnas
        form_frame.columnconfigure(1, weight=1)
        
        # Frame para resumen
        resumen_frame = ttk.LabelFrame(main_frame, text="Resumen del Pago", padding="10")
        resumen_frame.pack(fill='both', expand=True, pady=10)
        
        # Usar Text widget para mejor visualización del resumen
        bg_color = self.dialog.cget('bg')
        self.resumen_text = tk.Text(resumen_frame, height=6, font=('Arial', 10), 
                                    bg=bg_color, fg='black', wrap='word',
                                    relief='flat', borderwidth=0, padx=5, pady=5)
        self.resumen_text.pack(fill='both', expand=True)
        # Insertar texto inicial
        self.resumen_text.insert('1.0', 'Ingresa el monto para ver el resumen...')
        self.resumen_text.config(state='disabled')  # Solo lectura
        
        # Frame para botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(20, 0))
        
        # Botones - hacer el botón de confirmar más visible
        ttk.Button(button_frame, text="Confirmar Pago", command=self.guardar).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Cancelar", command=self.cancelar).pack(side='right')
        
        # Enfocar en el campo de monto
        self.monto_entry.focus()
        
        # Bind eventos
        self.monto_var.trace('w', lambda *args: self.calcular_resumen())
        self.dialog.bind('<Return>', lambda e: self.guardar())
        self.dialog.bind('<Escape>', lambda e: self.cancelar())
    
    def cargar_datos_prestamo(self):
        """Cargar información del préstamo"""
        prestamo = self.prestamo_data
        cuota_quincenal = prestamo.get('cuota_quincenal', 0)
        plazo_quincenas = prestamo.get('plazo_quincenas', 0)
        
        # Mostrar progreso (ej: 1/8, 2/8)
        progreso = f"{self.proxima_quincena}/{plazo_quincenas}"
        
        info_text = f"""Cliente: {prestamo['nombre_cliente']}
Monto del Préstamo: ${prestamo['monto_prestamo']:,.2f}
Cuota Quincenal: ${cuota_quincenal:,.2f}
Progreso: {progreso}
Saldo Pendiente: ${prestamo['saldo_pendiente']:,.2f}
Fecha de Inicio: {prestamo['fecha_inicio']}"""
        
        self.info_label.config(text=info_text)
        
        # Prellenar el monto con la cuota quincenal
        self.monto_var.set(f"{cuota_quincenal:.2f}")
        self.calcular_resumen()
    
    def calcular_resumen(self):
        """Calcular resumen del pago"""
        try:
            monto = float(self.monto_var.get() or 0)
            cuota_quincenal = self.prestamo_data.get('cuota_quincenal', 0)
            saldo_pendiente = self.prestamo_data['saldo_pendiente']
            plazo_quincenas = self.prestamo_data.get('plazo_quincenas', 0)
            
            # Calcular nuevo progreso después del pago
            nuevo_progreso = f"{self.proxima_quincena + 1}/{plazo_quincenas}" if abs(monto - cuota_quincenal) <= 0.01 else f"{self.proxima_quincena}/{plazo_quincenas}"
            
            # Formatear resumen con saltos de línea explícitos
            resumen_text = f"Monto a Pagar: ${monto:,.2f}\n" \
                          f"Cuota Quincenal Esperada: ${cuota_quincenal:,.2f}\n" \
                          f"Progreso después del pago: {nuevo_progreso}\n" \
                          f"Saldo Restante: ${max(0, saldo_pendiente - monto):,.2f}"
            
            # Mostrar advertencia si el monto no coincide
            if monto > 0 and abs(monto - cuota_quincenal) > 0.01:
                resumen_text += f"\n\n⚠ Advertencia: El monto debe ser ${cuota_quincenal:,.2f}"
            
            # Actualizar el widget Text
            self.resumen_text.config(state='normal')
            self.resumen_text.delete('1.0', tk.END)
            self.resumen_text.insert('1.0', resumen_text)
            self.resumen_text.config(state='disabled')
            
        except ValueError:
            self.resumen_text.config(state='normal')
            self.resumen_text.delete('1.0', tk.END)
            self.resumen_text.insert('1.0', "Ingresa un monto válido")
            self.resumen_text.config(state='disabled')
    
    def guardar(self):
        """Guardar datos del pago"""
        if not self.validar_datos():
            return
        
        try:
            fecha = self.fecha_var.get()
            monto = float(self.monto_var.get())
            recibido = self.recibido_var.get()
            
            # Mostrar diálogo de confirmación
            cliente = self.prestamo_data['nombre_cliente']
            confirmacion = f"¿Confirmar el registro del pago?\n\n" \
                          f"Cliente: {cliente}\n" \
                          f"Fecha: {fecha}\n" \
                          f"Monto: ${monto:,.2f}\n" \
                          f"Recibido por: {recibido or 'No especificado'}"
            
            if not messagebox.askyesno("Confirmar Pago", confirmacion, parent=self.dialog):
                return
            
            self.result = {
                'prestamo_id': self.prestamo_data['prestamo_id'],
                'fecha_pago': fecha,
                'monto_pago': monto,
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
        
        # Validar monto
        try:
            monto = float(self.monto_var.get())
            if monto <= 0:
                messagebox.showerror("Error", "El monto debe ser mayor a 0", parent=self.dialog)
                self.monto_entry.focus()
                return False
            
            cuota_quincenal = self.prestamo_data.get('cuota_quincenal', 0)
            if abs(monto - cuota_quincenal) > 0.01:
                messagebox.showerror("Error", f"El monto debe ser exactamente la cuota quincenal: ${cuota_quincenal:,.2f}", parent=self.dialog)
                self.monto_entry.focus()
                return False
        except ValueError:
            messagebox.showerror("Error", "El monto debe ser un número válido", parent=self.dialog)
            self.monto_entry.focus()
            return False
        
        # Validar que no exceda el saldo pendiente
        saldo_pendiente = self.prestamo_data['saldo_pendiente']
        if monto > saldo_pendiente:
            messagebox.showerror("Error", f"El monto del pago (${monto:,.2f}) excede el saldo pendiente (${saldo_pendiente:,.2f})", parent=self.dialog)
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
        
        # Título con estilo mejorado
        title_label = ttk.Label(main_frame, text="Gestión de Pagos", font=('Segoe UI', 18, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Frame superior para filtros y botones
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill='x', pady=(0, 10))
        
        # Filtros - usar Frame normal en lugar de LabelFrame para evitar colores no deseados
        filter_frame = tk.Frame(top_frame, bg='white', relief='flat', bd=1)
        filter_frame.pack(side='left', fill='x', expand=True, padx=5, pady=5)
        
        # Título de la sección
        title_label = tk.Label(filter_frame, text="Filtros", bg='white', fg='#2C3E50', font=('Segoe UI', 10, 'bold'))
        title_label.pack(anchor='w', pady=(10, 10), padx=10)
        
        # Contenedor interno con padding
        filter_content = tk.Frame(filter_frame, bg='white')
        filter_content.pack(fill='x', padx=10, pady=(0, 10))
        
        # Primera fila de filtros - usar Frame de tkinter normal para mejor compatibilidad de colores
        filter_row1 = tk.Frame(filter_content, bg='white')
        filter_row1.pack(fill='x', pady=(0, 5))
        
        tk.Label(filter_row1, text="Buscar por:", bg='white', fg='#2C3E50', font=('Segoe UI', 9)).pack(side='left', padx=(0, 5))
        self.tipo_busqueda = tk.StringVar(value="cliente")
        ttk.Radiobutton(filter_row1, text="Cliente", variable=self.tipo_busqueda, value="cliente", style='Filter.TRadiobutton').pack(side='left', padx=(0, 10))
        ttk.Radiobutton(filter_row1, text="Fecha", variable=self.tipo_busqueda, value="fecha", style='Filter.TRadiobutton').pack(side='left', padx=(0, 10))
        ttk.Radiobutton(filter_row1, text="Monto", variable=self.tipo_busqueda, value="monto", style='Filter.TRadiobutton').pack(side='left')
        
        # Segunda fila de filtros - usar Frame de tkinter normal
        filter_row2 = tk.Frame(filter_content, bg='white')
        filter_row2.pack(fill='x')
        
        tk.Label(filter_row2, text="Término:", bg='white', fg='#2C3E50', font=('Segoe UI', 9)).pack(side='left', padx=(0, 5))
        self.buscar_var = tk.StringVar()
        self.buscar_entry = ttk.Entry(filter_row2, textvariable=self.buscar_var, width=30)
        self.buscar_entry.pack(side='left', padx=(0, 10))
        
        tk.Label(filter_row2, text="Cliente:", bg='white', fg='#2C3E50', font=('Segoe UI', 9)).pack(side='left', padx=(0, 5))
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
        ttk.Button(button_frame, text="📄 Hoja de Recibos", command=self.generar_hoja_recibos).pack(side='left', padx=5)
        
        # Frame para la tabla
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill='both', expand=True)
        
        # Crear Treeview
        columns = ('ID', 'Cliente', 'Monto Préstamo', 'Cuota Quincenal', 'Progreso', 'Saldo Pendiente')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Configurar columnas
        self.tree.heading('ID', text='ID')
        self.tree.heading('Cliente', text='Cliente')
        self.tree.heading('Monto Préstamo', text='Monto del Préstamo')
        self.tree.heading('Cuota Quincenal', text='Cuota Quincenal')
        self.tree.heading('Progreso', text='Progreso')
        self.tree.heading('Saldo Pendiente', text='Saldo Pendiente')
        
        self.tree.column('ID', width=80, anchor='center')
        self.tree.column('Cliente', width=200)
        self.tree.column('Monto Préstamo', width=150, anchor='e')
        self.tree.column('Cuota Quincenal', width=150, anchor='e')
        self.tree.column('Progreso', width=100, anchor='center')
        self.tree.column('Saldo Pendiente', width=150, anchor='e')
        
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
                progreso = pago.get('progreso', '0/0')
                self.tree.insert('', 'end', values=(
                    pago['prestamo_id'],
                    pago['nombre_cliente'],
                    f"${pago['monto_prestamo']:,.2f}",
                    f"${pago['cuota_quincenal']:,.2f}",
                    progreso,
                    f"${pago['saldo_pendiente']:,.2f}"
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
                # Asegurar que tenga los campos necesarios
                monto_prestamo = pago.get('monto_prestamo', pago.get('monto_total', 0))
                cuota_quincenal = pago.get('cuota_quincenal', 0)
                saldo_pendiente = pago.get('saldo_pendiente', 0)
                progreso = pago.get('progreso', '0/0')
                
                self.tree.insert('', 'end', values=(
                    pago['prestamo_id'],
                    pago['nombre_cliente'],
                    f"${monto_prestamo:,.2f}",
                    f"${cuota_quincenal:,.2f}",
                    progreso,
                    f"${saldo_pendiente:,.2f}"
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
                dialog = PagoDialog(self, prestamo_data, self.model)
                self.wait_window(dialog.dialog)
                
                if dialog.result:
                    datos = dialog.result
                    pago_id = self.controller.registrar_pago(
                        datos['prestamo_id'],
                        datos['fecha_pago'],
                        datos['monto_pago'],
                        datos['recibido_por']
                    )
                    messagebox.showinfo("Éxito", "Pago registrado correctamente")
                    
                    # Generar recibo automáticamente
                    try:
                        from src.recibos import ReciboManager
                        recibo_manager = ReciboManager()
                        ruta_recibo = recibo_manager.generar_recibo_pago_individual(pago_id)
                        
                        # Preguntar si desea abrir el recibo
                        if messagebox.askyesno("Recibo Generado", 
                                             f"Recibo generado exitosamente.\n\n"
                                             f"Ubicación: {ruta_recibo}\n\n"
                                             f"¿Desea abrir el recibo ahora?",
                                             parent=self):
                            try:
                                if platform.system() == 'Windows':
                                    os.startfile(ruta_recibo)
                                elif platform.system() == 'Darwin':  # macOS
                                    subprocess.call(['open', ruta_recibo])
                                else:  # Linux
                                    subprocess.call(['xdg-open', ruta_recibo])
                            except Exception as e:
                                messagebox.showinfo("Información", 
                                                   f"No se pudo abrir el archivo automáticamente.\n"
                                                   f"Puede abrirlo manualmente desde:\n{ruta_recibo}")
                    except Exception as e:
                        messagebox.showwarning("Advertencia", 
                                             f"El pago se registró correctamente, pero hubo un error al generar el recibo:\n{e}")
                    
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
            # Obtener el último pago del préstamo
            historial = self.controller.obtener_historial_pagos(prestamo_id)
            if not historial:
                messagebox.showwarning("Advertencia", "Este préstamo no tiene pagos registrados")
                return
            
            # Obtener el último pago
            ultimo_pago = historial[-1]
            pago_id = ultimo_pago['id']
            
            # Generar recibo
            from src.recibos import ReciboManager
            recibo_manager = ReciboManager()
            ruta_recibo = recibo_manager.generar_recibo_pago_individual(pago_id)
            
            # Preguntar si desea abrir el recibo
            if messagebox.askyesno("Recibo Generado", 
                                 f"Recibo generado exitosamente.\n\n"
                                 f"Ubicación: {ruta_recibo}\n\n"
                                 f"¿Desea abrir el recibo ahora?",
                                 parent=self):
                try:
                    if platform.system() == 'Windows':
                        os.startfile(ruta_recibo)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.call(['open', ruta_recibo])
                    else:  # Linux
                        subprocess.call(['xdg-open', ruta_recibo])
                except Exception as e:
                    messagebox.showinfo("Información", 
                                       f"No se pudo abrir el archivo automáticamente.\n"
                                       f"Puede abrirlo manualmente desde:\n{ruta_recibo}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar recibo: {e}")
    
    def generar_hoja_recibos(self):
        """Generar hoja con recibos de todos los préstamos activos"""
        try:
            from src.recibos import ReciboManager
            recibo_manager = ReciboManager()
            
            # Mostrar mensaje de confirmación
            respuesta = messagebox.askyesno("Generar Hoja de Recibos", 
                                           "Se generará una hoja PDF con todos los préstamos activos.\n\n"
                                           "Cada recibo tendrá un borde para facilitar el recorte.\n\n"
                                           "¿Desea continuar?",
                                           parent=self)
            if not respuesta:
                return
            
            # Generar la hoja
            ruta_hoja = recibo_manager.generar_hoja_recibos_activos()
            
            # Preguntar si desea abrir el PDF
            if messagebox.askyesno("Hoja Generada", 
                                  f"Hoja de recibos generada exitosamente.\n\n"
                                  f"Ubicación: {ruta_hoja}\n\n"
                                  f"¿Desea abrir el archivo ahora?",
                                  parent=self):
                try:
                    if platform.system() == 'Windows':
                        os.startfile(ruta_hoja)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.call(['open', ruta_hoja])
                    else:  # Linux
                        subprocess.call(['xdg-open', ruta_hoja])
                except Exception as e:
                    messagebox.showinfo("Información", 
                                       f"No se pudo abrir el archivo automáticamente.\n"
                                       f"Puede abrirlo manualmente desde:\n{ruta_hoja}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar hoja de recibos: {e}")
    
    def generar_recibo_cliente(self):
        """Generar recibo en formato CAPTA VALE para el cliente seleccionado"""
        if not self.pago_seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un préstamo para generar el recibo del cliente", parent=self)
            return
        
        try:
            from src.recibos import ReciboManager
            recibo_manager = ReciboManager()
            
            # Obtener ID del cliente del préstamo seleccionado
            prestamo_id = self.pago_seleccionado[0]
            prestamo_data = self.controller.obtener_prestamo_para_pago(prestamo_id)
            
            if not prestamo_data:
                messagebox.showerror("Error", "No se pudo obtener información del préstamo", parent=self)
                return
            
            cliente_id = prestamo_data['cliente_id']
            
            # Generar recibo
            ruta_recibo = recibo_manager.generar_recibo_cliente_formato_capta(cliente_id)
            
            # Preguntar si desea abrir el PDF
            if messagebox.askyesno("Recibo Generado", 
                                  f"Recibo generado exitosamente.\n\n"
                                  f"Ubicación: {ruta_recibo}\n\n"
                                  f"¿Desea abrir el archivo ahora?",
                                  parent=self):
                try:
                    if platform.system() == 'Windows':
                        os.startfile(ruta_recibo)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.call(['open', ruta_recibo])
                    else:  # Linux
                        subprocess.call(['xdg-open', ruta_recibo])
                except Exception as e:
                    messagebox.showinfo("Información", 
                                       f"No se pudo abrir el archivo automáticamente.\n"
                                       f"Puede abrirlo manualmente desde:\n{ruta_recibo}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar recibo: {e}", parent=self)
    
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
    
    def registrar_pago(self, prestamo_id: int, fecha_pago: str, monto_pago: float, 
                      recibido_por: str = None) -> int:
        """Registrar nuevo pago con validaciones"""
        if monto_pago <= 0:
            raise ValueError("El monto del pago debe ser mayor a 0")
        
        return self.model.registrar_pago(prestamo_id, fecha_pago, monto_pago, recibido_por)
    
    def obtener_historial_pagos(self, prestamo_id: int) -> List[Dict]:
        """Obtener historial de pagos de un préstamo"""
        return self.model.obtener_historial_pagos(prestamo_id)
