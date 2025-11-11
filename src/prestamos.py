"""
Módulo para la gestión de préstamos
Funciones para crear, actualizar, consultar y calcular préstamos
"""

import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from dateutil.relativedelta import relativedelta
import math
import os
from tarifas import obtener_cuota_quincenal, calcular_total_pagar, calcular_interes_total, validar_monto_y_quincenas, QUINCENAS_DISPONIBLES, calcular_total_pagar as calc_total

def get_db_path():
    """Obtener la ruta absoluta de la base de datos"""
    # Obtener el directorio base del proyecto (un nivel arriba de src)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_dir = os.path.join(base_dir, 'database')
    db_path = os.path.join(db_dir, 'prestamos.db')
    return db_path

class PrestamoManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = get_db_path()
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtener conexión a la base de datos"""
        return sqlite3.connect(self.db_path)
    
    def crear_prestamo(self, cliente_id: int, monto: float, quincenas: int, 
                      fecha_inicio: str = None, tasa_interes: float = 0, 
                      fecha_primer_pago: str = None, detalles: str = None,
                      tiene_seguro: bool = False, beneficiario: str = None) -> int:
        """
        Crear un nuevo préstamo basado en la matriz de tarifas
        
        Args:
            cliente_id: ID del cliente
            monto: Monto del préstamo
            quincenas: Número de quincenas (6, 8, 10, 12, 14, 16)
            fecha_inicio: Fecha de inicio (formato YYYY-MM-DD, opcional)
            tasa_interes: Tasa de interés (se mantiene para compatibilidad, pero no se usa en el cálculo)
            fecha_primer_pago: Fecha del primer pago (formato YYYY-MM-DD, opcional)
            detalles: Detalles adicionales del préstamo
            tiene_seguro: Si el préstamo incluye seguro de $15
            beneficiario: Nombre del beneficiario del seguro
        
        Returns:
            int: ID del préstamo creado
        """
        try:
            # Validar monto y quincenas
            es_valido, mensaje = validar_monto_y_quincenas(monto, quincenas)
            if not es_valido:
                raise ValueError(mensaje)
            
            if fecha_inicio is None:
                fecha_inicio = date.today().isoformat()
            
            # Si no se proporciona fecha_primer_pago, usar fecha_inicio
            if fecha_primer_pago is None:
                fecha_primer_pago = fecha_inicio
            
            # Validar que si tiene seguro, debe tener beneficiario
            if tiene_seguro and not beneficiario:
                raise ValueError("Si el préstamo incluye seguro, debe especificar un beneficiario")
            
            # Calcular el interés total (diferencia entre total a pagar y monto)
            total_pagar = calcular_total_pagar(monto, quincenas)
            interes_total = calcular_interes_total(monto, quincenas)
            
            # Calcular tasa de interés equivalente (para mostrar en reportes)
            # Tasa = (interes_total / monto) * (24 / quincenas) * 100 (anualizada)
            if monto > 0:
                tasa_equivalente = (interes_total / monto) * (24 / quincenas) * 100
            else:
                tasa_equivalente = 0
            
            # Almacenar fecha_primer_pago en detalles si no hay detalles
            # Formato: "FECHA_PRIMER_PAGO:YYYY-MM-DD\n[detalles]"
            detalles_final = ""
            if fecha_primer_pago:
                detalles_final = f"FECHA_PRIMER_PAGO:{fecha_primer_pago}"
                if detalles:
                    detalles_final += f"\n{detalles}"
            elif detalles:
                detalles_final = detalles
            
            # Convertir tiene_seguro a entero (0 o 1)
            tiene_seguro_int = 1 if tiene_seguro else 0
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Verificar si los campos existen, si no, usar valores por defecto
                cursor.execute("PRAGMA table_info(prestamos)")
                columnas = cursor.fetchall()
                nombres_columnas = [col[1] for col in columnas]
                
                if 'tiene_seguro' in nombres_columnas and 'beneficiario' in nombres_columnas:
                    cursor.execute('''
                        INSERT INTO prestamos (cliente_id, monto_total, tasa_interes, plazo_quincenas, 
                                              fecha_inicio, detalles, tiene_seguro, beneficiario)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (cliente_id, monto, round(tasa_equivalente, 2), quincenas, fecha_inicio, 
                          detalles_final, tiene_seguro_int, beneficiario))
                else:
                    # Fallback para bases de datos sin los nuevos campos
                    cursor.execute('''
                        INSERT INTO prestamos (cliente_id, monto_total, tasa_interes, plazo_quincenas, fecha_inicio, detalles)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (cliente_id, monto, round(tasa_equivalente, 2), quincenas, fecha_inicio, detalles_final))
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
                # Verificar si los campos nuevos existen
                cursor.execute("PRAGMA table_info(prestamos)")
                columnas = cursor.fetchall()
                nombres_columnas = [col[1] for col in columnas]
                
                if 'tiene_seguro' in nombres_columnas and 'beneficiario' in nombres_columnas:
                    cursor.execute('''
                        SELECT p.id, p.cliente_id, c.nombre, p.monto_total, 
                               p.tasa_interes, p.plazo_quincenas, p.fecha_inicio, p.estado, 
                               p.detalles, p.tiene_seguro, p.beneficiario
                        FROM prestamos p
                        JOIN clientes c ON p.cliente_id = c.id
                        WHERE p.id = ?
                    ''', (prestamo_id,))
                else:
                    cursor.execute('''
                        SELECT p.id, p.cliente_id, c.nombre, p.monto_total, 
                               p.tasa_interes, p.plazo_quincenas, p.fecha_inicio, p.estado, p.detalles,
                               0, NULL
                        FROM prestamos p
                        JOIN clientes c ON p.cliente_id = c.id
                        WHERE p.id = ?
                    ''', (prestamo_id,))
                
                row = cursor.fetchone()
                
                if row:
                    detalles = row[8] or ''
                    fecha_primer_pago = None
                    
                    # Extraer fecha_primer_pago de detalles si existe
                    if detalles and detalles.startswith('FECHA_PRIMER_PAGO:'):
                        lines = detalles.split('\n', 1)
                        fecha_primer_pago = lines[0].replace('FECHA_PRIMER_PAGO:', '')
                        detalles = lines[1] if len(lines) > 1 else ''
                    
                    tiene_seguro = bool(row[9]) if len(row) > 9 else False
                    beneficiario = row[10] if len(row) > 10 else None
                    
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
                        'estado': row[7],
                        'detalles': detalles,
                        'fecha_primer_pago': fecha_primer_pago,
                        'tiene_seguro': tiene_seguro,
                        'beneficiario': beneficiario
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
                
                # Verificar si los campos nuevos existen
                cursor.execute("PRAGMA table_info(prestamos)")
                columnas = cursor.fetchall()
                nombres_columnas = [col[1] for col in columnas]
                
                if 'tiene_seguro' in nombres_columnas:
                    query = '''
                        SELECT p.id, p.cliente_id, c.nombre, p.monto_total, 
                               p.tiene_seguro, p.plazo_quincenas, p.fecha_inicio, p.estado
                        FROM prestamos p
                        JOIN clientes c ON p.cliente_id = c.id
                    '''
                else:
                    query = '''
                        SELECT p.id, p.cliente_id, c.nombre, p.monto_total, 
                               0, p.plazo_quincenas, p.fecha_inicio, p.estado
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
                    tiene_seguro = bool(row[4]) if len(row) > 4 else False
                    prestamos.append({
                        'id': row[0],
                        'cliente_id': row[1],
                        'nombre_cliente': row[2],
                        'apellido_cliente': '',  # No hay apellido en la BD
                        'monto': row[3],
                        'tiene_seguro': tiene_seguro,
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
                
                # Verificar si los campos nuevos existen
                cursor.execute("PRAGMA table_info(prestamos)")
                columnas = cursor.fetchall()
                nombres_columnas = [col[1] for col in columnas]
                
                if 'tiene_seguro' in nombres_columnas:
                    query = '''
                        SELECT p.id, p.cliente_id, c.nombre, p.monto_total, 
                               p.tiene_seguro, p.plazo_quincenas, p.fecha_inicio, p.estado
                        FROM prestamos p
                        JOIN clientes c ON p.cliente_id = c.id
                        WHERE 1=1
                    '''
                else:
                    query = '''
                        SELECT p.id, p.cliente_id, c.nombre, p.monto_total, 
                               0, p.plazo_quincenas, p.fecha_inicio, p.estado
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
                    tiene_seguro = bool(row[4]) if len(row) > 4 else False
                    prestamos.append({
                        'id': row[0],
                        'cliente_id': row[1],
                        'nombre_cliente': row[2],
                        'apellido_cliente': '',  # No hay apellido en la BD
                        'monto': row[3],
                        'tiene_seguro': tiene_seguro,
                        'plazo_quincenas': row[5],
                        'plazo_meses': row[5] / 2,  # Convertir quincenas a meses
                        'fecha_inicio': row[6],
                        'estado': row[7]
                    })
                
                return prestamos
                
        except sqlite3.Error as e:
            raise Exception(f"Error al buscar préstamos: {e}")
    
    def calcular_cuota_quincenal(self, monto: float, quincenas: int, tiene_seguro: bool = False) -> float:
        """
        Calcular la cuota quincenal de un préstamo basado en la matriz de tarifas
        
        Args:
            monto: Monto del préstamo
            quincenas: Número de quincenas (6, 8, 10, 12, 14, 16)
            tiene_seguro: Si el préstamo incluye seguro de $15
        
        Returns:
            float: Cuota quincenal (incluye $15 de seguro si aplica)
        """
        cuota_base = obtener_cuota_quincenal(monto, quincenas)
        if tiene_seguro:
            cuota_base += 15.0
        return round(cuota_base, 2)
    
    def calcular_cuota_mensual(self, monto: float, quincenas: int, tiene_seguro: bool = False) -> float:
        """
        Calcular la cuota mensual de un préstamo (equivalente a 2 cuotas quincenales)
        
        Args:
            monto: Monto del préstamo
            quincenas: Número de quincenas
            tiene_seguro: Si el préstamo incluye seguro de $15
        
        Returns:
            float: Cuota mensual (2 cuotas quincenales)
        """
        cuota_quincenal = self.calcular_cuota_quincenal(monto, quincenas, tiene_seguro)
        return round(cuota_quincenal * 2, 2)
    
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
    
    def eliminar_prestamo_completo(self, prestamo_id: int) -> bool:
        """
        Eliminar completamente un préstamo de la base de datos
        Esto también eliminará todos los pagos asociados (ON DELETE CASCADE)
        
        Args:
            prestamo_id: ID del préstamo a eliminar
        
        Returns:
            bool: True si se eliminó correctamente
        
        Raises:
            Exception: Si el préstamo tiene pagos registrados y no se puede eliminar
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar si tiene pagos registrados
                cursor.execute('SELECT COUNT(*) FROM pagos WHERE prestamo_id = ?', (prestamo_id,))
                tiene_pagos = cursor.fetchone()[0] > 0
                
                if tiene_pagos:
                    # Preguntar confirmación antes de eliminar
                    # (esto se manejará en la interfaz)
                    pass
                
                # Eliminar el préstamo (los pagos se eliminarán en cascada)
                cursor.execute('DELETE FROM prestamos WHERE id = ?', (prestamo_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise Exception(f"Error al eliminar préstamo: {e}")

# Funciones de conveniencia
def crear_prestamo(cliente_id: int, monto: float, quincenas: int, **kwargs) -> int:
    """Función de conveniencia para crear un préstamo"""
    manager = PrestamoManager()
    return manager.crear_prestamo(cliente_id, monto, quincenas, **kwargs)

def obtener_prestamo(prestamo_id: int) -> Optional[Dict]:
    """Función de conveniencia para obtener un préstamo"""
    manager = PrestamoManager()
    return manager.obtener_prestamo(prestamo_id)

def calcular_cuota_mensual(monto: float, quincenas: int) -> float:
    """Función de conveniencia para calcular cuota mensual"""
    manager = PrestamoManager()
    return manager.calcular_cuota_mensual(monto, quincenas)

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
        self.dialog.geometry("500x700")
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
        ttk.Label(form_frame, text="(Mínimo $1,000)", font=('Arial', 8), foreground='gray').grid(row=1, column=2, sticky='w', padx=(5, 0))
        
        # Plazo en quincenas (combobox con opciones disponibles)
        ttk.Label(form_frame, text="Quincenas *:").grid(row=2, column=0, sticky='w', pady=5)
        self.plazo_var = tk.StringVar()
        self.plazo_combo = ttk.Combobox(form_frame, textvariable=self.plazo_var, width=27, state='readonly')
        self.plazo_combo['values'] = QUINCENAS_DISPONIBLES
        self.plazo_combo.grid(row=2, column=1, sticky='ew', padx=(10, 0), pady=5)
        if not self.prestamo_data:
            self.plazo_combo.current(0)  # Seleccionar primera opción por defecto
        
        # Tasa de interés (oculto, se calcula automáticamente)
        self.tasa_var = tk.StringVar(value="0")
        
        # Fecha de inicio
        ttk.Label(form_frame, text="Fecha de Inicio:").grid(row=3, column=0, sticky='w', pady=5)
        self.fecha_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        self.fecha_entry = ttk.Entry(form_frame, textvariable=self.fecha_var, width=30)
        self.fecha_entry.grid(row=3, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Fecha del primer pago
        ttk.Label(form_frame, text="Primer Pago *:").grid(row=4, column=0, sticky='w', pady=5)
        self.primer_pago_var = tk.StringVar()
        self.primer_pago_combo = ttk.Combobox(form_frame, textvariable=self.primer_pago_var, width=27, state='readonly')
        self.primer_pago_combo.grid(row=4, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Actualizar opciones cuando cambie la fecha de inicio
        self.fecha_var.trace('w', lambda *args: self.actualizar_opciones_primer_pago())
        
        # Seguro
        self.tiene_seguro_var = tk.BooleanVar(value=False)
        self.seguro_check = ttk.Checkbutton(form_frame, text="Incluir seguro de $15", 
                                            variable=self.tiene_seguro_var,
                                            command=self.toggle_beneficiario)
        self.seguro_check.grid(row=5, column=1, sticky='w', padx=(10, 0), pady=5)
        
        # Beneficiario
        ttk.Label(form_frame, text="Beneficiario:").grid(row=6, column=0, sticky='w', pady=5)
        self.beneficiario_var = tk.StringVar()
        self.beneficiario_entry = ttk.Entry(form_frame, textvariable=self.beneficiario_var, width=30, state='disabled')
        self.beneficiario_entry.grid(row=6, column=1, sticky='ew', padx=(10, 0), pady=5)
        ttk.Label(form_frame, text="(Solo si incluye seguro)", font=('Arial', 8), foreground='gray').grid(row=6, column=2, sticky='w', padx=(5, 0))
        
        # Detalles
        ttk.Label(form_frame, text="Detalles:").grid(row=7, column=0, sticky='w', pady=5)
        self.detalles_text = tk.Text(form_frame, height=4, width=30)
        self.detalles_text.grid(row=7, column=1, sticky='ew', padx=(10, 0), pady=5)
        
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
        self.plazo_var.trace('w', lambda *args: self.calcular_preview())
        self.tiene_seguro_var.trace('w', lambda *args: self.calcular_preview())
        self.dialog.bind('<Return>', lambda e: self.guardar())
        self.dialog.bind('<Escape>', lambda e: self.cancelar())
        
        # Inicializar opciones de primer pago
        self.actualizar_opciones_primer_pago()
    
    def actualizar_opciones_primer_pago(self):
        """Actualizar opciones de fecha del primer pago basándose en la fecha de inicio"""
        try:
            fecha_str = self.fecha_var.get()
            if not fecha_str:
                return
            
            fecha_inicio = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            hoy = date.today()
            
            # Calcular las opciones de primer pago (15 o 30)
            opciones = []
            
            # Obtener año y mes de la fecha de inicio
            año = fecha_inicio.year
            mes = fecha_inicio.month
            dia = fecha_inicio.day
            
            # Calcular fecha del 15 y 30 del mes actual
            fecha_15_actual = date(año, mes, 15)
            fecha_30_actual = date(año, mes, 30)
            
            # Calcular fecha del 15 y 30 del mes siguiente
            if mes == 12:
                fecha_15_siguiente = date(año + 1, 1, 15)
                fecha_30_siguiente = date(año + 1, 1, 30)
            else:
                fecha_15_siguiente = date(año, mes + 1, 15)
                fecha_30_siguiente = date(año, mes + 1, 30)
            
            # Meses en español
            meses_es = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                       'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
            
            # Si la fecha de inicio es antes del 15, puede pagar el 15 o 30 del mismo mes
            if dia < 15:
                if fecha_15_actual >= hoy:
                    mes_nombre = meses_es[fecha_15_actual.month - 1]
                    opciones.append(f"{fecha_15_actual.strftime('%Y-%m-%d')} (15 de {mes_nombre})")
                if fecha_30_actual >= hoy:
                    mes_nombre = meses_es[fecha_30_actual.month - 1]
                    opciones.append(f"{fecha_30_actual.strftime('%Y-%m-%d')} (30 de {mes_nombre})")
                # También puede pagar el 15 del mes siguiente
                if fecha_15_siguiente >= hoy:
                    mes_nombre = meses_es[fecha_15_siguiente.month - 1]
                    opciones.append(f"{fecha_15_siguiente.strftime('%Y-%m-%d')} (15 de {mes_nombre})")
            # Si la fecha de inicio es entre el 15 y 30, puede pagar el 30 del mismo mes o 15 del siguiente
            elif dia < 30:
                if fecha_30_actual >= hoy:
                    mes_nombre = meses_es[fecha_30_actual.month - 1]
                    opciones.append(f"{fecha_30_actual.strftime('%Y-%m-%d')} (30 de {mes_nombre})")
                if fecha_15_siguiente >= hoy:
                    mes_nombre = meses_es[fecha_15_siguiente.month - 1]
                    opciones.append(f"{fecha_15_siguiente.strftime('%Y-%m-%d')} (15 de {mes_nombre})")
            # Si la fecha de inicio es el 30 o después, solo puede pagar el 15 del mes siguiente
            else:
                if fecha_15_siguiente >= hoy:
                    mes_nombre = meses_es[fecha_15_siguiente.month - 1]
                    opciones.append(f"{fecha_15_siguiente.strftime('%Y-%m-%d')} (15 de {mes_nombre})")
                if fecha_30_siguiente >= hoy:
                    mes_nombre = meses_es[fecha_30_siguiente.month - 1]
                    opciones.append(f"{fecha_30_siguiente.strftime('%Y-%m-%d')} (30 de {mes_nombre})")
            
            # Si no hay opciones válidas, agregar al menos el 15 del mes siguiente
            if not opciones:
                meses_es = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                           'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
                mes_nombre = meses_es[fecha_15_siguiente.month - 1]
                opciones.append(f"{fecha_15_siguiente.strftime('%Y-%m-%d')} (15 de {mes_nombre})")
            
            self.primer_pago_combo['values'] = opciones
            if opciones and not self.prestamo_data:
                self.primer_pago_combo.current(0)  # Seleccionar primera opción por defecto
                
        except (ValueError, AttributeError):
            # Si hay error en el formato de fecha, no hacer nada
            pass
    
    def toggle_beneficiario(self):
        """Habilitar/deshabilitar campo de beneficiario según el checkbox de seguro"""
        if self.tiene_seguro_var.get():
            self.beneficiario_entry.config(state='normal')
        else:
            self.beneficiario_entry.config(state='disabled')
            self.beneficiario_var.set("")
    
    def cargar_datos(self):
        """Cargar datos existentes si es edición"""
        if self.prestamo_data:
            # Buscar cliente en la lista
            for cliente in self.clientes_data:
                if cliente[0] == self.prestamo_data['cliente_id']:
                    self.cliente_var.set(f"{cliente[0]} - {cliente[1]}")
                    break
            
            self.monto_var.set(str(self.prestamo_data['monto']))
            self.plazo_var.set(str(self.prestamo_data['plazo_quincenas']))
            self.fecha_var.set(self.prestamo_data['fecha_inicio'])
            self.detalles_text.insert('1.0', self.prestamo_data.get('detalles', ''))
            
            # Cargar seguro y beneficiario si existen
            tiene_seguro = self.prestamo_data.get('tiene_seguro', False)
            self.tiene_seguro_var.set(tiene_seguro)
            if tiene_seguro:
                self.beneficiario_entry.config(state='normal')
                beneficiario = self.prestamo_data.get('beneficiario', '')
                self.beneficiario_var.set(beneficiario)
            
            # Cargar fecha del primer pago si existe
            if 'fecha_primer_pago' in self.prestamo_data:
                fecha_primer_pago = self.prestamo_data['fecha_primer_pago']
                # Buscar en las opciones y seleccionar
                self.actualizar_opciones_primer_pago()
                for i, opcion in enumerate(self.primer_pago_combo['values']):
                    if opcion.startswith(fecha_primer_pago):
                        self.primer_pago_combo.current(i)
                        break
    
    def calcular_preview(self):
        """Calcular vista previa de los pagos usando la matriz de tarifas"""
        try:
            monto_str = self.monto_var.get().strip()
            plazo_str = self.plazo_var.get().strip()
            
            if not monto_str or not plazo_str:
                self.preview_text.config(state='normal')
                self.preview_text.delete('1.0', tk.END)
                self.preview_text.insert('1.0', "Ingresa monto y quincenas para ver el cálculo")
                self.preview_text.config(state='disabled')
                return
            
            monto = float(monto_str)
            quincenas = int(plazo_str)
            
            # Validar
            es_valido, mensaje = validar_monto_y_quincenas(monto, quincenas)
            if not es_valido:
                self.preview_text.config(state='normal')
                self.preview_text.delete('1.0', tk.END)
                self.preview_text.insert('1.0', f"Error: {mensaje}")
                self.preview_text.config(state='disabled')
                return
            
            # Obtener si tiene seguro
            tiene_seguro = self.tiene_seguro_var.get()
            
            # Calcular usando la matriz de tarifas
            cuota_base = obtener_cuota_quincenal(monto, quincenas)
            cuota_quincenal = cuota_base + (15.0 if tiene_seguro else 0.0)
            cuota_mensual = cuota_quincenal * 2
            total_pagar = calcular_total_pagar(monto, quincenas) + (15.0 * quincenas if tiene_seguro else 0.0)
            total_interes = calcular_interes_total(monto, quincenas) + (15.0 * quincenas if tiene_seguro else 0.0)
            plazo_meses = quincenas / 2
            
            seguro_text = f"\n   • Seguro: ${15.0 * quincenas:,.2f} (${15.0:.2f} por quincena)" if tiene_seguro else ""
            
            preview = f"""RESUMEN DEL PRESTAMO

Monto solicitado: ${monto:,.2f}
Plazo: {quincenas} quincenas ({plazo_meses:.1f} meses)
Seguro: {"Sí ($15 por quincena)" if tiene_seguro else "No"}

CUOTAS:
   • Cuota quincenal base: ${cuota_base:,.2f}{" + $15.00 seguro" if tiene_seguro else ""}
   • Cuota quincenal total: ${cuota_quincenal:,.2f}
   • Cuota mensual: ${cuota_mensual:,.2f}

TOTALES:
   • Total a pagar: ${total_pagar:,.2f}{seguro_text}
   • Total intereses: ${total_interes:,.2f}"""
            
            self.preview_text.config(state='normal')
            self.preview_text.delete('1.0', tk.END)
            self.preview_text.insert('1.0', preview)
            self.preview_text.config(state='disabled')
                
        except ValueError as e:
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
            quincenas = int(self.plazo_var.get())
            fecha = self.fecha_var.get()
            primer_pago_str = self.primer_pago_var.get()
            detalles = self.detalles_text.get('1.0', tk.END).strip()
            tiene_seguro = self.tiene_seguro_var.get()
            beneficiario = self.beneficiario_var.get().strip() if tiene_seguro else None
            
            # Extraer fecha del primer pago del string (formato: "YYYY-MM-DD (descripción)")
            fecha_primer_pago = primer_pago_str.split(' ')[0] if primer_pago_str else None
            
            # Validar monto y quincenas
            es_valido, mensaje = validar_monto_y_quincenas(monto, quincenas)
            if not es_valido:
                messagebox.showerror("Error", mensaje, parent=self.dialog)
                return
            
            # Validar que si tiene seguro, debe tener beneficiario
            if tiene_seguro and not beneficiario:
                messagebox.showerror("Error", "Si incluye seguro, debe especificar un beneficiario", parent=self.dialog)
                self.beneficiario_entry.focus()
                return
            
            self.result = {
                'cliente_id': cliente_id,
                'monto': monto,
                'quincenas': quincenas,
                'fecha_inicio': fecha,
                'fecha_primer_pago': fecha_primer_pago,
                'detalles': detalles,
                'tiene_seguro': tiene_seguro,
                'beneficiario': beneficiario
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
        
        # Validar fecha del primer pago
        primer_pago = self.primer_pago_var.get()
        if not primer_pago:
            messagebox.showerror("Error", "Debes seleccionar la fecha del primer pago", parent=self.dialog)
            self.primer_pago_combo.focus()
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
        ttk.Button(button_frame, text="Cancelar", command=self.cancelar_prestamo).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Eliminar", command=self.eliminar_prestamo).pack(side='left', padx=5)
        
        # Frame para la tabla
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill='both', expand=True)
        
        # Crear Treeview
        columns = ('ID', 'Cliente', 'Monto', 'Seguro', 'Plazo', 'Fecha Inicio', 'Estado')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Configurar columnas
        self.tree.heading('ID', text='ID')
        self.tree.heading('Cliente', text='Cliente')
        self.tree.heading('Monto', text='Monto')
        self.tree.heading('Seguro', text='Seguro')
        self.tree.heading('Plazo', text='Plazo')
        self.tree.heading('Fecha Inicio', text='Fecha Inicio')
        self.tree.heading('Estado', text='Estado')
        
        self.tree.column('ID', width=50, anchor='center')
        self.tree.column('Cliente', width=200)
        self.tree.column('Monto', width=100, anchor='e')
        self.tree.column('Seguro', width=80, anchor='center')
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
                seguro_text = "Sí ($15)" if prestamo.get('tiene_seguro', False) else "No"
                self.tree.insert('', 'end', values=(
                    prestamo['id'],
                    prestamo['nombre_cliente'],
                    f"${prestamo['monto']:,.2f}",
                    seguro_text,
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
                seguro_text = "Sí ($15)" if prestamo.get('tiene_seguro', False) else "No"
                self.tree.insert('', 'end', values=(
                    prestamo['id'],
                    prestamo['nombre_cliente'],
                    f"${prestamo['monto']:,.2f}",
                    seguro_text,
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
                    datos['quincenas'],
                    datos['fecha_inicio'],
                    datos.get('fecha_primer_pago'),
                    datos.get('detalles', ''),
                    datos.get('tiene_seguro', False),
                    datos.get('beneficiario')
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
            tiene_seguro = prestamo.get('tiene_seguro', False)
            cuota_quincenal = self.model.calcular_cuota_quincenal(prestamo['monto'], prestamo['plazo_quincenas'], tiene_seguro)
            cuota_mensual = self.model.calcular_cuota_mensual(prestamo['monto'], prestamo['plazo_quincenas'], tiene_seguro)
            total_pagar = calcular_total_pagar(prestamo['monto'], prestamo['plazo_quincenas']) + (15.0 * prestamo['plazo_quincenas'] if tiene_seguro else 0.0)
            
            # Información de seguro
            seguro_info = ""
            if prestamo.get('tiene_seguro', False):
                beneficiario = prestamo.get('beneficiario', 'No especificado')
                seguro_info = f"Seguro: Sí ($15)\nBeneficiario: {beneficiario}\n"
            else:
                seguro_info = "Seguro: No\n"
            
            info_text = f"""INFORMACION DEL PRESTAMO

ID: {prestamo['id']}
Cliente: {prestamo['nombre_cliente']}
Monto: ${prestamo['monto']:,.2f}
{seguro_info}Plazo: {prestamo['plazo_quincenas']} quincenas ({prestamo['plazo_meses']:.1f} meses)
Fecha de Inicio: {prestamo['fecha_inicio']}
Estado: {prestamo['estado']}

CUOTAS:
   • Cuota quincenal: ${cuota_quincenal:,.2f}
   • Cuota mensual: ${cuota_mensual:,.2f}
   • Total a pagar: ${total_pagar:,.2f}"""
            
            ttk.Label(main_frame, text=info_text, font=('Arial', 12), justify='left').pack(pady=20)
            
            # Botón cerrar
            ttk.Button(main_frame, text="Cerrar", command=detail_window.destroy).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al mostrar detalles: {e}")
    
    def cancelar_prestamo(self):
        """Cancelar préstamo seleccionado (marcar como CANCELADO pero mantener registro)"""
        if not self.prestamo_seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un préstamo para cancelar")
            return
        
        try:
            prestamo_id = self.prestamo_seleccionado[0]
            # Obtener datos completos del préstamo desde la base de datos
            prestamo = self.controller.obtener_prestamo(prestamo_id)
            
            if not prestamo:
                messagebox.showerror("Error", "No se pudo obtener la información del préstamo")
                return
            
            cliente_nombre = prestamo['nombre_cliente']
            monto = prestamo['monto']
            estado_actual = prestamo['estado']
            
            if estado_actual == "CANCELADO":
                messagebox.showinfo("Información", "Este préstamo ya está cancelado")
                return
            
            # Confirmar cancelación
            respuesta = messagebox.askyesno(
                "Confirmar Cancelación",
                f"¿Estás seguro de cancelar el préstamo #{prestamo_id}?\n\n"
                f"Cliente: {cliente_nombre}\n"
                f"Monto: ${monto:,.2f}\n\n"
                f"El préstamo quedará marcado como CANCELADO pero se mantendrá en el registro."
            )
            
            if respuesta:
                self.controller.cancelar_prestamo(prestamo_id)
                messagebox.showinfo("Éxito", "Préstamo cancelado correctamente")
                self.listar_prestamos()
        
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def eliminar_prestamo(self):
        """Eliminar completamente el préstamo seleccionado de la base de datos"""
        if not self.prestamo_seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un préstamo para eliminar")
            return
        
        try:
            prestamo_id = self.prestamo_seleccionado[0]
            # Obtener datos completos del préstamo desde la base de datos
            prestamo = self.controller.obtener_prestamo(prestamo_id)
            
            if not prestamo:
                messagebox.showerror("Error", "No se pudo obtener la información del préstamo")
                return
            
            cliente_nombre = prestamo['nombre_cliente']
            monto = prestamo['monto']
            
            # Verificar si tiene pagos registrados
            pagos = self.controller.verificar_pagos_prestamo(prestamo_id)
            tiene_pagos = len(pagos) > 0
            
            if tiene_pagos:
                mensaje = (
                    f"ADVERTENCIA: Este préstamo tiene {len(pagos)} pago(s) registrado(s).\n\n"
                    f"Cliente: {cliente_nombre}\n"
                    f"Monto: ${monto:,.2f}\n\n"
                    f"Si eliminas este préstamo, TODOS los pagos asociados también se eliminarán permanentemente.\n\n"
                    f"¿Estás SEGURO de que quieres eliminar completamente este préstamo?"
                )
            else:
                mensaje = (
                    f"¿Estás seguro de eliminar COMPLETAMENTE el préstamo #{prestamo_id}?\n\n"
                    f"Cliente: {cliente_nombre}\n"
                    f"Monto: ${monto:,.2f}\n\n"
                    f"Esta acción NO se puede deshacer. El préstamo será eliminado permanentemente."
                )
            
            # Confirmar eliminación
            respuesta = messagebox.askyesno(
                "Confirmar Eliminación Completa",
                mensaje,
                icon='warning' if tiene_pagos else 'question'
            )
            
            if respuesta:
                self.controller.eliminar_prestamo_completo(prestamo_id)
                messagebox.showinfo("Éxito", "Préstamo eliminado completamente de la base de datos")
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
    
    def crear_prestamo(self, cliente_id: int, monto: float, quincenas: int, 
                      fecha_inicio: str, fecha_primer_pago: str = None, 
                      detalles: str = '', tiene_seguro: bool = False, 
                      beneficiario: str = None) -> int:
        """Crear nuevo préstamo con validaciones basado en matriz de tarifas"""
        # Validar monto y quincenas
        es_valido, mensaje = validar_monto_y_quincenas(monto, quincenas)
        if not es_valido:
            raise ValueError(mensaje)
        
        return self.model.crear_prestamo(cliente_id, monto, quincenas, fecha_inicio, 
                                        detalles=detalles, fecha_primer_pago=fecha_primer_pago,
                                        tiene_seguro=tiene_seguro, beneficiario=beneficiario)
    
    def modificar_prestamo(self, prestamo_id: int, datos: Dict) -> bool:
        """Modificar préstamo con validaciones"""
        # TODO: Implementar modificación de préstamos
        raise NotImplementedError("La modificación de préstamos no está implementada aún")
    
    def cancelar_prestamo(self, prestamo_id: int) -> bool:
        """Cancelar préstamo (marcar como CANCELADO pero mantener registro)"""
        return self.model.actualizar_estado_prestamo(prestamo_id, 'CANCELADO')
    
    def eliminar_prestamo_completo(self, prestamo_id: int) -> bool:
        """Eliminar completamente un préstamo de la base de datos"""
        return self.model.eliminar_prestamo_completo(prestamo_id)
    
    def verificar_pagos_prestamo(self, prestamo_id: int) -> List[Dict]:
        """Verificar si un préstamo tiene pagos registrados"""
        try:
            with self.model.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, fecha_pago, monto_capital + monto_interes + monto_seguro as total
                    FROM pagos 
                    WHERE prestamo_id = ?
                    ORDER BY fecha_pago
                ''', (prestamo_id,))
                rows = cursor.fetchall()
                return [{'id': row[0], 'fecha': row[1], 'total': row[2]} for row in rows]
        except sqlite3.Error as e:
            raise Exception(f"Error al verificar pagos: {e}")
