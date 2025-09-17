"""
Módulo para la gestión de préstamos
Funciones para crear, actualizar, consultar y calcular préstamos
"""

import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from dateutil.relativedelta import relativedelta
import math

class PrestamoManager:
    def __init__(self, db_path: str = '../database/prestamos.db'):
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtener conexión a la base de datos"""
        return sqlite3.connect(self.db_path)
    
    def crear_prestamo(self, cliente_id: int, monto: float, tasa_interes: float, 
                      plazo_meses: int, fecha_inicio: str = None) -> int:
        """
        Crear un nuevo préstamo
        
        Args:
            cliente_id: ID del cliente
            monto: Monto del préstamo
            tasa_interes: Tasa de interés anual (porcentaje)
            plazo_meses: Plazo en meses
            fecha_inicio: Fecha de inicio (formato YYYY-MM-DD, opcional)
        
        Returns:
            int: ID del préstamo creado
        """
        try:
            if fecha_inicio is None:
                fecha_inicio = date.today().isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO prestamos (cliente_id, monto_total, tasa_interes, plazo_quincenas, fecha_inicio)
                    VALUES (?, ?, ?, ?, ?)
                ''', (cliente_id, monto, tasa_interes, plazo_meses * 2, fecha_inicio))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            raise Exception(f"Error al crear préstamo: {e}")
    
    def obtener_prestamo(self, prestamo_id: int) -> Optional[Dict]:
        """
        Obtener un préstamo por su ID
        
        Args:
            prestamo_id: ID del préstamo
        
        Returns:
            Dict con los datos del préstamo o None si no existe
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.id, p.cliente_id, c.nombre, p.monto_total, 
                           p.tasa_interes, p.plazo_quincenas, p.fecha_inicio, p.estado
                    FROM prestamos p
                    JOIN clientes c ON p.cliente_id = c.id
                    WHERE p.id = ?
                ''', (prestamo_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'cliente_id': row[1],
                        'nombre_cliente': row[2],
                        'apellido_cliente': '',  # No hay apellido en la BD
                        'monto': row[3],
                        'tasa_interes': row[4],
                        'plazo_quincenas': row[5],
                        'plazo_meses': row[5] / 2,  # Convertir quincenas a meses
                        'fecha_inicio': row[6],
                        'estado': row[7]
                    }
                return None
        except sqlite3.Error as e:
            raise Exception(f"Error al obtener préstamo: {e}")
    
    def listar_prestamos(self, cliente_id: int = None, estado: str = None) -> List[Dict]:
        """
        Listar préstamos con filtros opcionales
        
        Args:
            cliente_id: Filtrar por cliente específico (opcional)
            estado: Filtrar por estado (opcional)
        
        Returns:
            Lista de diccionarios con los datos de los préstamos
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT p.id, p.cliente_id, c.nombre, p.monto_total, 
                           p.tasa_interes, p.plazo_quincenas, p.fecha_inicio, p.estado
                    FROM prestamos p
                    JOIN clientes c ON p.cliente_id = c.id
                '''
                params = []
                
                conditions = []
                if cliente_id:
                    conditions.append("p.cliente_id = ?")
                    params.append(cliente_id)
                if estado:
                    conditions.append("p.estado = ?")
                    params.append(estado)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY p.fecha_inicio DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                prestamos = []
                
                for row in rows:
                    prestamos.append({
                        'id': row[0],
                        'cliente_id': row[1],
                        'nombre_cliente': row[2],
                        'apellido_cliente': '',  # No hay apellido en la BD
                        'monto': row[3],
                        'tasa_interes': row[4],
                        'plazo_quincenas': row[5],
                        'plazo_meses': row[5] / 2,  # Convertir quincenas a meses
                        'fecha_inicio': row[6],
                        'estado': row[7]
                    })
                
                return prestamos
        except sqlite3.Error as e:
            raise Exception(f"Error al listar préstamos: {e}")
    
    def buscar_prestamos_avanzado(self, termino: str, tipo: str, estado: str) -> List[Dict]:
        """
        Buscar préstamos por término, tipo y estado
        
        Args:
            termino: Término de búsqueda
            tipo: Tipo de búsqueda (cliente, monto, id)
            estado: Estado del préstamo
        
        Returns:
            Lista de diccionarios con los préstamos encontrados
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT p.id, p.cliente_id, c.nombre, p.monto_total, 
                           p.tasa_interes, p.plazo_quincenas, p.fecha_inicio, p.estado
                    FROM prestamos p
                    JOIN clientes c ON p.cliente_id = c.id
                    WHERE 1=1
                '''
                
                params = []
                
                # Agregar filtro por término según tipo
                if termino:
                    if tipo == "cliente":
                        query += " AND c.nombre LIKE ?"
                        params.append(f'%{termino}%')
                    elif tipo == "monto":
                        try:
                            monto = float(termino)
                            query += " AND p.monto_total = ?"
                            params.append(monto)
                        except ValueError:
                            # Si no es un número, buscar como texto
                            query += " AND CAST(p.monto_total AS TEXT) LIKE ?"
                            params.append(f'%{termino}%')
                    elif tipo == "id":
                        try:
                            prestamo_id = int(termino)
                            query += " AND p.id = ?"
                            params.append(prestamo_id)
                        except ValueError:
                            # Si no es un número, buscar como texto
                            query += " AND CAST(p.id AS TEXT) LIKE ?"
                            params.append(f'%{termino}%')
                
                # Agregar filtro por estado
                if estado and estado != "TODOS":
                    query += " AND p.estado = ?"
                    params.append(estado)
                
                query += " ORDER BY p.fecha_inicio DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                prestamos = []
                for row in rows:
                    prestamos.append({
                        'id': row[0],
                        'cliente_id': row[1],
                        'nombre_cliente': row[2],
                        'apellido_cliente': '',  # No hay apellido en la BD
                        'monto': row[3],
                        'tasa_interes': row[4],
                        'plazo_quincenas': row[5],
                        'plazo_meses': row[5] / 2,  # Convertir quincenas a meses
                        'fecha_inicio': row[6],
                        'estado': row[7]
                    })
                
                return prestamos
                
        except sqlite3.Error as e:
            raise Exception(f"Error al buscar préstamos: {e}")
    
    def calcular_cuota_mensual(self, monto: float, tasa_interes: float, plazo_meses: int) -> float:
        """
        Calcular la cuota mensual de un préstamo
        
        Args:
            monto: Monto del préstamo
            tasa_interes: Tasa de interés anual (porcentaje)
            plazo_meses: Plazo en meses
        
        Returns:
            float: Cuota mensual
        """
        # Convertir tasa anual a mensual
        tasa_mensual = tasa_interes / 12 / 100
        
        if tasa_mensual == 0:
            return monto / plazo_meses
        
        # Fórmula de cuota fija
        cuota = monto * (tasa_mensual * (1 + tasa_mensual) ** plazo_meses) / ((1 + tasa_mensual) ** plazo_meses - 1)
        return round(cuota, 2)
    
    def actualizar_estado_prestamo(self, prestamo_id: int, estado: str) -> bool:
        """
        Actualizar el estado de un préstamo
        
        Args:
            prestamo_id: ID del préstamo
            estado: Nuevo estado ('ACTIVO', 'PAGADO', 'VENCIDO', 'CANCELADO')
        
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE prestamos SET estado = ? WHERE id = ?
                ''', (estado, prestamo_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise Exception(f"Error al actualizar estado del préstamo: {e}")

# Funciones de conveniencia
def crear_prestamo(cliente_id: int, monto: float, tasa_interes: float, plazo_meses: int, **kwargs) -> int:
    """Función de conveniencia para crear un préstamo"""
    manager = PrestamoManager()
    return manager.crear_prestamo(cliente_id, monto, tasa_interes, plazo_meses, **kwargs)

def obtener_prestamo(prestamo_id: int) -> Optional[Dict]:
    """Función de conveniencia para obtener un préstamo"""
    manager = PrestamoManager()
    return manager.obtener_prestamo(prestamo_id)

def calcular_cuota_mensual(monto: float, tasa_interes: float, plazo_meses: int) -> float:
    """Función de conveniencia para calcular cuota mensual"""
    manager = PrestamoManager()
    return manager.calcular_cuota_mensual(monto, tasa_interes, plazo_meses)

# ============================================================================
# INTERFAZ GRÁFICA - PRESTAMOSWINDOW
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import math

class PrestamoDialog:
    """Diálogo para crear/editar préstamos"""
    
    def __init__(self, parent, clientes_data: List[Tuple], prestamo_data: Optional[Dict] = None):
        self.parent = parent
        self.clientes_data = clientes_data
        self.prestamo_data = prestamo_data
        self.result = None
        
        # Crear ventana de diálogo
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Editar Préstamo" if prestamo_data else "Nuevo Préstamo")
        self.dialog.geometry("500x600")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrar diálogo
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.crear_widgets()
        self.cargar_datos()
        self.calcular_preview()
    
    def crear_widgets(self):
        """Crear widgets del diálogo"""
        # Frame principal
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Título
        titulo = "Editar Préstamo" if self.prestamo_data else "Nuevo Préstamo"
        ttk.Label(main_frame, text=titulo, font=('Arial', 14, 'bold')).pack(pady=(0, 20))
        
        # Frame para formulario
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill='x', pady=10)
        
        # Cliente
        ttk.Label(form_frame, text="Cliente *:").grid(row=0, column=0, sticky='w', pady=5)
        self.cliente_var = tk.StringVar()
        self.cliente_combo = ttk.Combobox(form_frame, textvariable=self.cliente_var, width=30, state='readonly')
        self.cliente_combo.grid(row=0, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Cargar clientes en combobox
        clientes_options = [f"{c[0]} - {c[1]}" for c in self.clientes_data]
        self.cliente_combo['values'] = clientes_options
        
        # Monto
        ttk.Label(form_frame, text="Monto Total *:").grid(row=1, column=0, sticky='w', pady=5)
        self.monto_var = tk.StringVar()
        self.monto_entry = ttk.Entry(form_frame, textvariable=self.monto_var, width=30)
        self.monto_entry.grid(row=1, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Tasa de interés
        ttk.Label(form_frame, text="Tasa de Interés (%) *:").grid(row=2, column=0, sticky='w', pady=5)
        self.tasa_var = tk.StringVar()
        self.tasa_entry = ttk.Entry(form_frame, textvariable=self.tasa_var, width=30)
        self.tasa_entry.grid(row=2, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Plazo en quincenas
        ttk.Label(form_frame, text="Plazo (quincenas) *:").grid(row=3, column=0, sticky='w', pady=5)
        self.plazo_var = tk.StringVar()
        self.plazo_entry = ttk.Entry(form_frame, textvariable=self.plazo_var, width=30)
        self.plazo_entry.grid(row=3, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Fecha de inicio
        ttk.Label(form_frame, text="Fecha de Inicio:").grid(row=4, column=0, sticky='w', pady=5)
        self.fecha_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        self.fecha_entry = ttk.Entry(form_frame, textvariable=self.fecha_var, width=30)
        self.fecha_entry.grid(row=4, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Detalles
        ttk.Label(form_frame, text="Detalles:").grid(row=5, column=0, sticky='w', pady=5)
        self.detalles_text = tk.Text(form_frame, height=4, width=30)
        self.detalles_text.grid(row=5, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Configurar expansión de columnas
        form_frame.columnconfigure(1, weight=1)
        
        # Frame para preview de cálculos
        preview_frame = ttk.LabelFrame(main_frame, text="Vista Previa de Cálculos", padding="10")
        preview_frame.pack(fill='x', pady=10)
        
        self.preview_text = tk.Text(preview_frame, height=8, width=50, state='disabled')
        self.preview_text.pack(fill='x')
        
        # Frame para botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(20, 0))
        
        # Botones
        ttk.Button(button_frame, text="Calcular", command=self.calcular_preview).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="Guardar", command=self.guardar).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Cancelar", command=self.cancelar).pack(side='right')
        
        # Enfocar en el primer campo
        self.cliente_combo.focus()
        
        # Bind eventos
        self.monto_var.trace('w', lambda *args: self.calcular_preview())
        self.tasa_var.trace('w', lambda *args: self.calcular_preview())
        self.plazo_var.trace('w', lambda *args: self.calcular_preview())
        self.dialog.bind('<Return>', lambda e: self.guardar())
        self.dialog.bind('<Escape>', lambda e: self.cancelar())
    
    def cargar_datos(self):
        """Cargar datos existentes si es edición"""
        if self.prestamo_data:
            # Buscar cliente en la lista
            for cliente in self.clientes_data:
                if cliente[0] == self.prestamo_data['cliente_id']:
                    self.cliente_var.set(f"{cliente[0]} - {cliente[1]}")
                    break
            
            self.monto_var.set(str(self.prestamo_data['monto']))
            self.tasa_var.set(str(self.prestamo_data['tasa_interes']))
            self.plazo_var.set(str(self.prestamo_data['plazo_quincenas']))
            self.fecha_var.set(self.prestamo_data['fecha_inicio'])
            self.detalles_text.insert('1.0', self.prestamo_data.get('detalles', ''))
    
    def calcular_preview(self):
        """Calcular vista previa de los pagos"""
        try:
            monto = float(self.monto_var.get() or 0)
            tasa = float(self.tasa_var.get() or 0)
            plazo = int(self.plazo_var.get() or 0)
            
            if monto > 0 and tasa >= 0 and plazo > 0:
                # Convertir plazo de quincenas a meses
                plazo_meses = plazo / 2
                
                # Calcular cuota mensual
                tasa_mensual = tasa / 12 / 100
                if tasa_mensual == 0:
                    cuota_mensual = monto / plazo_meses
                else:
                    cuota_mensual = monto * (tasa_mensual * (1 + tasa_mensual) ** plazo_meses) / ((1 + tasa_mensual) ** plazo_meses - 1)
                
                # Calcular cuota quincenal
                cuota_quincenal = cuota_mensual / 2
                
                # Calcular total a pagar
                total_pagar = cuota_mensual * plazo_meses
                total_interes = total_pagar - monto
                
                preview = f"""📊 RESUMEN DEL PRÉSTAMO

💰 Monto solicitado: ${monto:,.2f}
📅 Plazo: {plazo} quincenas ({plazo_meses:.1f} meses)
📈 Tasa de interés: {tasa}% anual

💳 CUOTAS:
   • Cuota mensual: ${cuota_mensual:,.2f}
   • Cuota quincenal: ${cuota_quincenal:,.2f}

📋 TOTALES:
   • Total a pagar: ${total_pagar:,.2f}
   • Total intereses: ${total_interes:,.2f}"""
                
                self.preview_text.config(state='normal')
                self.preview_text.delete('1.0', tk.END)
                self.preview_text.insert('1.0', preview)
                self.preview_text.config(state='disabled')
            else:
                self.preview_text.config(state='normal')
                self.preview_text.delete('1.0', tk.END)
                self.preview_text.insert('1.0', "Ingresa los datos para ver el cálculo")
                self.preview_text.config(state='disabled')
                
        except ValueError:
            self.preview_text.config(state='normal')
            self.preview_text.delete('1.0', tk.END)
            self.preview_text.insert('1.0', "Datos inválidos")
            self.preview_text.config(state='disabled')
    
    def guardar(self):
        """Guardar datos del préstamo"""
        if not self.validar_datos():
            return
        
        try:
            # Obtener ID del cliente
            cliente_seleccionado = self.cliente_var.get()
            cliente_id = None
            for cliente in self.clientes_data:
                if f"{cliente[0]} - {cliente[1]}" == cliente_seleccionado:
                    cliente_id = cliente[0]
                    break
            
            # Obtener valores validados
            monto = float(self.monto_var.get())
            tasa = float(self.tasa_var.get())
            plazo = int(self.plazo_var.get())
            fecha = self.fecha_var.get()
            detalles = self.detalles_text.get('1.0', tk.END).strip()
            
            self.result = {
                'cliente_id': cliente_id,
                'monto': monto,
                'tasa_interes': tasa,
                'plazo_quincenas': plazo,
                'fecha_inicio': fecha,
                'detalles': detalles
            }
            
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Dato inválido: {e}", parent=self.dialog)
    
    def validar_datos(self):
        """Validar datos del formulario"""
        # Validar cliente
        cliente_seleccionado = self.cliente_var.get()
        if not cliente_seleccionado:
            messagebox.showerror("Error", "Debes seleccionar un cliente", parent=self.dialog)
            self.cliente_combo.focus()
            return False
        
        # Validar monto
        try:
            monto = float(self.monto_var.get())
            if monto <= 0:
                messagebox.showerror("Error", "El monto debe ser mayor a 0", parent=self.dialog)
                self.monto_entry.focus()
                return False
            if monto > 1000000:  # Límite de 1 millón
                messagebox.showerror("Error", "El monto no puede exceder $1,000,000", parent=self.dialog)
                self.monto_entry.focus()
                return False
        except ValueError:
            messagebox.showerror("Error", "El monto debe ser un número válido", parent=self.dialog)
            self.monto_entry.focus()
            return False
        
        # Validar tasa
        try:
            tasa = float(self.tasa_var.get())
            if tasa < 0:
                messagebox.showerror("Error", "La tasa de interés no puede ser negativa", parent=self.dialog)
                self.tasa_entry.focus()
                return False
            if tasa > 100:  # Límite del 100%
                messagebox.showerror("Error", "La tasa de interés no puede exceder el 100%", parent=self.dialog)
                self.tasa_entry.focus()
                return False
        except ValueError:
            messagebox.showerror("Error", "La tasa debe ser un número válido", parent=self.dialog)
            self.tasa_entry.focus()
            return False
        
        # Validar plazo
        try:
            plazo = int(self.plazo_var.get())
            if plazo <= 0:
                messagebox.showerror("Error", "El plazo debe ser mayor a 0", parent=self.dialog)
                self.plazo_entry.focus()
                return False
            if plazo > 120:  # Máximo 10 años (120 quincenas)
                messagebox.showerror("Error", "El plazo no puede exceder 120 quincenas (10 años)", parent=self.dialog)
                self.plazo_entry.focus()
                return False
        except ValueError:
            messagebox.showerror("Error", "El plazo debe ser un número entero válido", parent=self.dialog)
            self.plazo_entry.focus()
            return False
        
        # Validar fecha
        fecha = self.fecha_var.get()
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
            fecha_actual = datetime.now()
            if fecha_obj > fecha_actual:
                messagebox.showerror("Error", "La fecha de inicio no puede ser futura", parent=self.dialog)
                self.fecha_entry.focus()
                return False
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido (YYYY-MM-DD)", parent=self.dialog)
            self.fecha_entry.focus()
            return False
        
        return True
    
    def cancelar(self):
        """Cancelar operación"""
        self.result = None
        self.dialog.destroy()

class PrestamosWindow(ttk.Frame):
    """Ventana principal de gestión de préstamos"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # Inicializar modelo y controlador
        self.model = PrestamoManager()
        self.controller = PrestamoController(self.model)
        
        # Variables
        self.prestamo_seleccionado = None
        self.clientes_data = []
        
        # Crear interfaz
        self.cargar_clientes()
        self.crear_widgets()
        self.listar_prestamos()
    
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
        ttk.Label(main_frame, text="Gestión de Préstamos", font=('Arial', 16, 'bold')).pack(pady=(0, 20))
        
        # Frame superior para filtros y botones
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill='x', pady=(0, 10))
        
        # Filtros avanzados
        filter_frame = ttk.LabelFrame(top_frame, text="Búsqueda y Filtros", padding="10")
        filter_frame.pack(side='left', fill='x', expand=True)
        
        # Primera fila de filtros
        filter_row1 = ttk.Frame(filter_frame)
        filter_row1.pack(fill='x', pady=(0, 5))
        
        ttk.Label(filter_row1, text="Buscar por:").pack(side='left', padx=(0, 5))
        self.tipo_busqueda = tk.StringVar(value="cliente")
        ttk.Radiobutton(filter_row1, text="Cliente", variable=self.tipo_busqueda, value="cliente").pack(side='left', padx=(0, 10))
        ttk.Radiobutton(filter_row1, text="Monto", variable=self.tipo_busqueda, value="monto").pack(side='left', padx=(0, 10))
        ttk.Radiobutton(filter_row1, text="ID Préstamo", variable=self.tipo_busqueda, value="id").pack(side='left')
        
        # Segunda fila de filtros
        filter_row2 = ttk.Frame(filter_frame)
        filter_row2.pack(fill='x')
        
        ttk.Label(filter_row2, text="Término:").pack(side='left', padx=(0, 5))
        self.buscar_var = tk.StringVar()
        self.buscar_entry = ttk.Entry(filter_row2, textvariable=self.buscar_var, width=30)
        self.buscar_entry.pack(side='left', padx=(0, 10))
        
        ttk.Label(filter_row2, text="Estado:").pack(side='left', padx=(0, 5))
        self.estado_var = tk.StringVar(value="TODOS")
        estado_combo = ttk.Combobox(filter_row2, textvariable=self.estado_var, 
                                   values=["TODOS", "ACTIVO", "PAGADO", "VENCIDO", "CANCELADO"], 
                                   width=15, state='readonly')
        estado_combo.pack(side='left', padx=(0, 10))
        
        ttk.Button(filter_row2, text="🔍 Buscar", command=self.buscar_prestamos).pack(side='left', padx=(0, 5))
        ttk.Button(filter_row2, text="🔄 Limpiar", command=self.limpiar_filtros).pack(side='left')
        
        # Botones principales
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side='right')
        
        ttk.Button(button_frame, text="Nuevo Préstamo", command=self.nuevo_prestamo).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Editar Préstamo", command=self.editar_prestamo).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Ver Detalles", command=self.ver_detalles).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Eliminar", command=self.eliminar_prestamo).pack(side='left', padx=5)
        
        # Frame para la tabla
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill='both', expand=True)
        
        # Crear Treeview
        columns = ('ID', 'Cliente', 'Monto', 'Tasa', 'Plazo', 'Fecha Inicio', 'Estado')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Configurar columnas
        self.tree.heading('ID', text='ID')
        self.tree.heading('Cliente', text='Cliente')
        self.tree.heading('Monto', text='Monto')
        self.tree.heading('Tasa', text='Tasa %')
        self.tree.heading('Plazo', text='Plazo')
        self.tree.heading('Fecha Inicio', text='Fecha Inicio')
        self.tree.heading('Estado', text='Estado')
        
        self.tree.column('ID', width=50, anchor='center')
        self.tree.column('Cliente', width=200)
        self.tree.column('Monto', width=100, anchor='e')
        self.tree.column('Tasa', width=80, anchor='center')
        self.tree.column('Plazo', width=80, anchor='center')
        self.tree.column('Fecha Inicio', width=100, anchor='center')
        self.tree.column('Estado', width=100, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Empaquetar tabla y scrollbar
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind eventos
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        self.tree.bind('<Double-1>', lambda e: self.ver_detalles())
    
    def listar_prestamos(self):
        """Listar todos los préstamos en la tabla"""
        try:
            # Limpiar tabla
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Obtener préstamos
            prestamos = self.controller.obtener_lista_prestamos()
            
            # Insertar en tabla
            for prestamo in prestamos:
                self.tree.insert('', 'end', values=(
                    prestamo['id'],
                    prestamo['nombre_cliente'],
                    f"${prestamo['monto']:,.2f}",
                    f"{prestamo['tasa_interes']}%",
                    f"{prestamo['plazo_quincenas']} quincenas",
                    prestamo['fecha_inicio'],
                    prestamo['estado']
                ))
            
            # Actualizar estado
            self.actualizar_estado()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al listar préstamos: {e}")
    
    def buscar_prestamos(self):
        """Buscar préstamos por término y tipo"""
        try:
            termino = self.buscar_var.get().strip()
            tipo = self.tipo_busqueda.get()
            estado = self.estado_var.get()
            
            if not termino and estado == "TODOS":
                self.listar_prestamos()
                return
            
            # Limpiar tabla
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Obtener préstamos filtrados
            prestamos = self.controller.buscar_prestamos_avanzado(termino, tipo, estado)
            
            # Insertar en tabla
            for prestamo in prestamos:
                self.tree.insert('', 'end', values=(
                    prestamo['id'],
                    prestamo['nombre_cliente'],
                    f"${prestamo['monto']:,.2f}",
                    f"{prestamo['tasa_interes']}%",
                    f"{prestamo['plazo_quincenas']} quincenas",
                    prestamo['fecha_inicio'],
                    prestamo['estado']
                ))
            
            # Mostrar resultado de búsqueda
            if termino:
                if prestamos:
                    messagebox.showinfo("Búsqueda", f"Se encontraron {len(prestamos)} préstamo(s) con '{termino}' en {tipo}")
                else:
                    messagebox.showinfo("Búsqueda", f"No se encontraron préstamos con '{termino}' en {tipo}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar préstamos: {e}")
    
    def limpiar_filtros(self):
        """Limpiar filtros y mostrar todos los préstamos"""
        self.buscar_var.set("")
        self.estado_var.set("TODOS")
        self.listar_prestamos()
    
    def nuevo_prestamo(self):
        """Abrir diálogo para nuevo préstamo"""
        if not self.clientes_data:
            messagebox.showwarning("Advertencia", "No hay clientes disponibles. Crea clientes primero.")
            return
        
        dialog = PrestamoDialog(self, self.clientes_data)
        self.wait_window(dialog.dialog)
        
        if dialog.result:
            try:
                datos = dialog.result
                self.controller.crear_prestamo(
                    datos['cliente_id'],
                    datos['monto'],
                    datos['tasa_interes'],
                    datos['plazo_quincenas'],
                    datos['fecha_inicio'],
                    datos['detalles']
                )
                messagebox.showinfo("Éxito", "Préstamo creado correctamente")
                self.listar_prestamos()
            except Exception as e:
                messagebox.showerror("Error", str(e))
    
    def editar_prestamo(self):
        """Abrir diálogo para editar préstamo"""
        if not self.prestamo_seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un préstamo para editar")
            return
        
        try:
            prestamo_id = self.prestamo_seleccionado[0]
            prestamo_data = self.controller.obtener_prestamo(prestamo_id)
            
            if prestamo_data:
                dialog = PrestamoDialog(self, self.clientes_data, prestamo_data)
                self.wait_window(dialog.dialog)
                
                if dialog.result:
                    datos = dialog.result
                    self.controller.modificar_prestamo(prestamo_id, datos)
                    messagebox.showinfo("Éxito", "Préstamo actualizado correctamente")
                    self.listar_prestamos()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al editar préstamo: {e}")
    
    def ver_detalles(self):
        """Ver detalles del préstamo seleccionado"""
        if not self.prestamo_seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un préstamo para ver detalles")
            return
        
        try:
            prestamo_id = self.prestamo_seleccionado[0]
            prestamo = self.controller.obtener_prestamo(prestamo_id)
            if prestamo:
                self.mostrar_detalles_prestamo(prestamo)
        except Exception as e:
            messagebox.showerror("Error", f"Error al mostrar detalles: {e}")
    
    def mostrar_detalles_prestamo(self, prestamo: Dict):
        """Mostrar ventana de detalles del préstamo"""
        try:
            # Crear ventana de detalles
            detail_window = tk.Toplevel(self)
            detail_window.title(f"Detalles del Préstamo #{prestamo['id']}")
            detail_window.geometry("600x400")
            
            # Frame principal
            main_frame = ttk.Frame(detail_window, padding="20")
            main_frame.pack(fill='both', expand=True)
            
            # Información del préstamo
            info_text = f"""📋 INFORMACIÓN DEL PRÉSTAMO

🆔 ID: {prestamo['id']}
👤 Cliente: {prestamo['nombre_cliente']}
💰 Monto: ${prestamo['monto']:,.2f}
📈 Tasa de Interés: {prestamo['tasa_interes']}% anual
📅 Plazo: {prestamo['plazo_quincenas']} quincenas ({prestamo['plazo_meses']:.1f} meses)
📆 Fecha de Inicio: {prestamo['fecha_inicio']}
📊 Estado: {prestamo['estado']}

💳 CUOTA MENSUAL: ${self.model.calcular_cuota_mensual(prestamo['monto'], prestamo['tasa_interes'], prestamo['plazo_meses']):,.2f}"""
            
            ttk.Label(main_frame, text=info_text, font=('Arial', 12), justify='left').pack(pady=20)
            
            # Botón cerrar
            ttk.Button(main_frame, text="Cerrar", command=detail_window.destroy).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al mostrar detalles: {e}")
    
    def eliminar_prestamo(self):
        """Eliminar préstamo seleccionado"""
        if not self.prestamo_seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un préstamo para eliminar")
            return
        
        try:
            prestamo_id = self.prestamo_seleccionado[0]
            cliente_nombre = self.prestamo_seleccionado[1]
            monto = self.prestamo_seleccionado[2]
            
            # Confirmar eliminación
            respuesta = messagebox.askyesno(
                "Confirmar Eliminación",
                f"¿Estás seguro de que quieres eliminar el préstamo?\n\n"
                f"Cliente: {cliente_nombre}\n"
                f"Monto: {monto}\n\n"
                f"Esta acción no se puede deshacer."
            )
            
            if respuesta:
                self.controller.eliminar_prestamo(prestamo_id)
                messagebox.showinfo("Éxito", "Préstamo eliminado correctamente")
                self.listar_prestamos()
        
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def on_select(self, event):
        """Manejar selección de préstamo"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            self.prestamo_seleccionado = item['values']
        else:
            self.prestamo_seleccionado = None
        
        self.actualizar_estado()
    
    def actualizar_estado(self):
        """Actualizar estado de botones según selección"""
        tiene_seleccion = self.prestamo_seleccionado is not None
        
        # Habilitar/deshabilitar botones según contexto
        for child in self.winfo_children():
            if isinstance(child, ttk.Frame):
                for button in child.winfo_children():
                    if isinstance(button, ttk.Frame):
                        for btn in button.winfo_children():
                            if isinstance(btn, ttk.Button):
                                if "Editar" in btn['text'] or "Ver Detalles" in btn['text'] or "Eliminar" in btn['text']:
                                    btn['state'] = 'normal' if tiene_seleccion else 'disabled'

class PrestamoController:
    """Controlador para la lógica de negocio de préstamos"""
    
    def __init__(self, model: PrestamoManager):
        self.model = model
    
    def obtener_lista_prestamos(self) -> List[Dict]:
        """Obtener lista de todos los préstamos"""
        return self.model.listar_prestamos()
    
    def obtener_prestamos_por_estado(self, estado: str) -> List[Dict]:
        """Obtener préstamos por estado"""
        return self.model.listar_prestamos(estado=estado)
    
    def buscar_prestamos_avanzado(self, termino: str, tipo: str, estado: str) -> List[Dict]:
        """Buscar préstamos por término, tipo y estado"""
        return self.model.buscar_prestamos_avanzado(termino, tipo, estado)
    
    def obtener_prestamo(self, prestamo_id: int) -> Optional[Dict]:
        """Obtener préstamo específico"""
        return self.model.obtener_prestamo(prestamo_id)
    
    def crear_prestamo(self, cliente_id: int, monto: float, tasa_interes: float, 
                      plazo_quincenas: int, fecha_inicio: str, detalles: str = '') -> int:
        """Crear nuevo préstamo con validaciones"""
        if monto <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        
        if tasa_interes < 0:
            raise ValueError("La tasa de interés no puede ser negativa")
        
        if plazo_quincenas <= 0:
            raise ValueError("El plazo debe ser mayor a 0")
        
        # Convertir plazo de quincenas a meses
        plazo_meses = plazo_quincenas / 2
        
        return self.model.crear_prestamo(cliente_id, monto, tasa_interes, plazo_meses, fecha_inicio)
    
    def modificar_prestamo(self, prestamo_id: int, datos: Dict) -> bool:
        """Modificar préstamo con validaciones"""
        # TODO: Implementar modificación de préstamos
        raise NotImplementedError("La modificación de préstamos no está implementada aún")
    
    def eliminar_prestamo(self, prestamo_id: int) -> bool:
        """Eliminar préstamo con validaciones"""
        # Verificar si el préstamo tiene pagos registrados
        # TODO: Implementar verificación de pagos
        return self.model.actualizar_estado_prestamo(prestamo_id, 'CANCELADO')
