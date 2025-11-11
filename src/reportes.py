#!/usr/bin/env python3
"""
Módulo para la generación de reportes
Funciones para generar reportes de estado de cuenta, ingresos y vencimientos
"""

import sqlite3
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from dateutil.relativedelta import relativedelta
import math
import os

def get_db_path():
    """Obtener la ruta absoluta de la base de datos"""
    # Obtener el directorio base del proyecto (un nivel arriba de src)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_dir = os.path.join(base_dir, 'database')
    db_path = os.path.join(db_dir, 'prestamos.db')
    return db_path

class ReporteManager:
    """Modelo para la gestión de reportes"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = get_db_path()
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtener conexión a la base de datos"""
        return sqlite3.connect(self.db_path)
    
    def generar_estado_cuenta(self, cliente_id: int) -> Dict:
        """
        Generar estado de cuenta para un cliente
        
        Args:
            cliente_id: ID del cliente
        
        Returns:
            Diccionario con el estado de cuenta
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Obtener información del cliente
                cursor.execute('''
                    SELECT id, nombre, telefono, direccion, fecha_registro
                    FROM clientes WHERE id = ?
                ''', (cliente_id,))
                
                cliente = cursor.fetchone()
                if not cliente:
                    raise Exception("Cliente no encontrado")
                
                # Obtener préstamos del cliente
                cursor.execute('''
                    SELECT id, monto_total, tasa_interes, fecha_inicio, plazo_quincenas, estado, detalles
                    FROM prestamos 
                    WHERE cliente_id = ?
                    ORDER BY fecha_inicio DESC
                ''', (cliente_id,))
                
                prestamos = cursor.fetchall()
                
                # Calcular totales
                total_prestado = sum(p[1] for p in prestamos)
                total_pagado = 0
                saldo_pendiente = 0
                prestamos_activos = 0
                
                for prestamo in prestamos:
                    prestamo_id = prestamo[0]
                    
                    # Obtener pagos del préstamo
                    cursor.execute('''
                        SELECT SUM(monto_capital + monto_interes + monto_seguro)
                        FROM pagos WHERE prestamo_id = ?
                    ''', (prestamo_id,))
                    
                    pagado = cursor.fetchone()[0] or 0
                    total_pagado += pagado
                    
                    if prestamo[5] == 'ACTIVO':  # estado
                        prestamos_activos += 1
                        saldo_pendiente += (prestamo[1] - pagado)
                
                return {
                    'cliente': {
                        'id': cliente[0],
                        'nombre': cliente[1],
                        'telefono': cliente[2],
                        'direccion': cliente[3],
                        'fecha_registro': cliente[4]
                    },
                    'prestamos': prestamos,
                    'totales': {
                        'total_prestado': total_prestado,
                        'total_pagado': total_pagado,
                        'saldo_pendiente': saldo_pendiente,
                        'prestamos_activos': prestamos_activos
                    },
                    'fecha_reporte': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
        except sqlite3.Error as e:
            raise Exception(f"Error al generar estado de cuenta: {e}")
    
    def generar_resumen_ingresos(self, fecha_inicio: str, fecha_fin: str) -> Dict:
        """
        Generar resumen de ingresos por período
        
        Args:
            fecha_inicio: Fecha de inicio (YYYY-MM-DD)
            fecha_fin: Fecha de fin (YYYY-MM-DD)
        
        Returns:
            Diccionario con el resumen de ingresos
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Obtener pagos del período
                cursor.execute('''
                    SELECT 
                        p.id as pago_id,
                        p.fecha_pago,
                        p.monto_capital,
                        p.monto_interes,
                        p.monto_seguro,
                        c.nombre as nombre_cliente,
                        pr.id as prestamo_id
                    FROM pagos p
                    JOIN prestamos pr ON p.prestamo_id = pr.id
                    JOIN clientes c ON pr.cliente_id = c.id
                    WHERE p.fecha_pago BETWEEN ? AND ?
                    ORDER BY p.fecha_pago
                ''', (fecha_inicio, fecha_fin))
                
                pagos = cursor.fetchall()
                
                # Calcular totales
                total_capital = sum(p[2] for p in pagos)
                total_interes = sum(p[3] for p in pagos)
                total_seguro = sum(p[4] for p in pagos)
                total_ingresos = total_capital + total_interes + total_seguro
                
                # Agrupar por día
                ingresos_por_dia = {}
                for pago in pagos:
                    fecha = pago[1]
                    monto_total = pago[2] + pago[3] + pago[4]
                    
                    if fecha in ingresos_por_dia:
                        ingresos_por_dia[fecha] += monto_total
                    else:
                        ingresos_por_dia[fecha] = monto_total
                
                # Obtener estadísticas adicionales
                cursor.execute('''
                    SELECT COUNT(DISTINCT pr.cliente_id)
                    FROM pagos p
                    JOIN prestamos pr ON p.prestamo_id = pr.id
                    WHERE p.fecha_pago BETWEEN ? AND ?
                ''', (fecha_inicio, fecha_fin))
                
                clientes_activos = cursor.fetchone()[0]
                
                return {
                    'periodo': {
                        'fecha_inicio': fecha_inicio,
                        'fecha_fin': fecha_fin
                    },
                    'pagos': pagos,
                    'totales': {
                        'total_capital': total_capital,
                        'total_interes': total_interes,
                        'total_seguro': total_seguro,
                        'total_ingresos': total_ingresos,
                        'num_pagos': len(pagos),
                        'clientes_activos': clientes_activos
                    },
                    'ingresos_por_dia': ingresos_por_dia,
                    'fecha_reporte': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
        except sqlite3.Error as e:
            raise Exception(f"Error al generar resumen de ingresos: {e}")
    
    def obtener_prestamos_proximos_vencer(self, dias_adelanto: int = 30) -> List[Dict]:
        """
        Obtener préstamos próximos a vencer
        
        Args:
            dias_adelanto: Días de adelanto para la alerta
        
        Returns:
            Lista de préstamos próximos a vencer
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Calcular fecha límite
                fecha_limite = datetime.now() + timedelta(days=dias_adelanto)
                
                # Obtener préstamos activos próximos a vencer
                cursor.execute('''
                    SELECT 
                        p.id,
                        p.monto_total,
                        p.tasa_interes,
                        p.fecha_inicio,
                        p.plazo_quincenas,
                        p.estado,
                        c.nombre as nombre_cliente,
                        c.telefono,
                        COALESCE(SUM(pag.monto_capital + pag.monto_interes + pag.monto_seguro), 0) as total_pagado
                    FROM prestamos p
                    JOIN clientes c ON p.cliente_id = c.id
                    LEFT JOIN pagos pag ON p.id = pag.prestamo_id
                    WHERE p.estado = 'ACTIVO'
                    GROUP BY p.id, p.monto_total, p.tasa_interes, p.fecha_inicio, p.plazo_quincenas, p.estado, c.nombre, c.telefono
                ''')
                
                prestamos = cursor.fetchall()
                prestamos_proximos = []
                
                for prestamo in prestamos:
                    prestamo_id, monto_total, tasa_interes, fecha_inicio, plazo_quincenas, estado, nombre_cliente, telefono, total_pagado = prestamo
                    
                    # Calcular fecha de vencimiento
                    fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                    fecha_vencimiento = fecha_inicio_obj + relativedelta(months=plazo_quincenas//2)
                    
                    # Verificar si está próximo a vencer
                    if fecha_vencimiento <= fecha_limite:
                        dias_restantes = (fecha_vencimiento - datetime.now()).days
                        saldo_pendiente = monto_total - total_pagado
                        
                        prestamos_proximos.append({
                            'prestamo_id': prestamo_id,
                            'cliente': nombre_cliente,
                            'telefono': telefono,
                            'monto_total': monto_total,
                            'total_pagado': total_pagado,
                            'saldo_pendiente': saldo_pendiente,
                            'fecha_inicio': fecha_inicio,
                            'fecha_vencimiento': fecha_vencimiento.strftime('%Y-%m-%d'),
                            'dias_restantes': dias_restantes,
                            'plazo_quincenas': plazo_quincenas,
                            'tasa_interes': tasa_interes
                        })
                
                # Ordenar por días restantes
                prestamos_proximos.sort(key=lambda x: x['dias_restantes'])
                
                return prestamos_proximos
                
        except sqlite3.Error as e:
            raise Exception(f"Error al obtener préstamos próximos a vencer: {e}")
    
    def generar_reporte_mensual(self, mes: int, año: int) -> Dict:
        """
        Generar reporte mensual completo
        
        Args:
            mes: Mes (1-12)
            año: Año
        
        Returns:
            Diccionario con el reporte mensual
        """
        try:
            fecha_inicio = f"{año:04d}-{mes:02d}-01"
            if mes == 12:
                fecha_fin = f"{año+1:04d}-01-01"
            else:
                fecha_fin = f"{año:04d}-{mes+1:02d}-01"
            
            # Obtener resumen de ingresos
            resumen_ingresos = self.generar_resumen_ingresos(fecha_inicio, fecha_fin)
            
            # Obtener préstamos próximos a vencer
            prestamos_proximos = self.obtener_prestamos_proximos_vencer(30)
            
            # Obtener estadísticas adicionales
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Nuevos préstamos del mes
                cursor.execute('''
                    SELECT COUNT(*), SUM(monto_total)
                    FROM prestamos 
                    WHERE fecha_inicio BETWEEN ? AND ?
                ''', (fecha_inicio, fecha_fin))
                
                nuevos_prestamos = cursor.fetchone()
                num_nuevos_prestamos = nuevos_prestamos[0] or 0
                monto_nuevos_prestamos = nuevos_prestamos[1] or 0
                
                # Préstamos pagados del mes
                cursor.execute('''
                    SELECT COUNT(*)
                    FROM prestamos 
                    WHERE estado = 'PAGADO' 
                    AND fecha_creacion BETWEEN ? AND ?
                ''', (fecha_inicio, fecha_fin))
                
                prestamos_pagados = cursor.fetchone()[0] or 0
                
                # Clientes activos
                cursor.execute('''
                    SELECT COUNT(DISTINCT cliente_id)
                    FROM prestamos 
                    WHERE estado = 'ACTIVO'
                ''')
                
                clientes_activos = cursor.fetchone()[0] or 0
            
            return {
                'periodo': {
                    'mes': mes,
                    'año': año,
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                },
                'ingresos': resumen_ingresos,
                'prestamos_proximos': prestamos_proximos,
                'estadisticas': {
                    'nuevos_prestamos': num_nuevos_prestamos,
                    'monto_nuevos_prestamos': monto_nuevos_prestamos,
                    'prestamos_pagados': prestamos_pagados,
                    'clientes_activos': clientes_activos
                },
                'fecha_reporte': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except sqlite3.Error as e:
            raise Exception(f"Error al generar reporte mensual: {e}")

# ============================================================================
# INTERFAZ GRÁFICA - REPORTESWINDOW
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date
import os

class ReporteDialog:
    """Diálogo para configurar reportes"""
    
    def __init__(self, parent, tipo_reporte: str):
        self.parent = parent
        self.tipo_reporte = tipo_reporte
        self.result = None
        
        # Crear ventana de diálogo
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Configurar Reporte - {tipo_reporte}")
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrar diálogo
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.crear_widgets()
    
    def crear_widgets(self):
        """Crear widgets del diálogo"""
        # Frame principal
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Título
        ttk.Label(main_frame, text=f"Configurar {self.tipo_reporte}", font=('Arial', 14, 'bold')).pack(pady=(0, 20))
        
        # Frame para parámetros
        params_frame = ttk.LabelFrame(main_frame, text="Parámetros", padding="10")
        params_frame.pack(fill='x', pady=(0, 20))
        
        if self.tipo_reporte == "Estado de Cuenta":
            # Selección de cliente
            ttk.Label(params_frame, text="Cliente:").grid(row=0, column=0, sticky='w', pady=5)
            self.cliente_var = tk.StringVar()
            self.cliente_combo = ttk.Combobox(params_frame, textvariable=self.cliente_var, width=30, state='readonly')
            self.cliente_combo.grid(row=0, column=1, sticky='ew', padx=(10, 0), pady=5)
            
            # Cargar clientes
            self.cargar_clientes()
            
        elif self.tipo_reporte == "Resumen de Ingresos":
            # Fecha inicio
            ttk.Label(params_frame, text="Fecha Inicio:").grid(row=0, column=0, sticky='w', pady=5)
            self.fecha_inicio_var = tk.StringVar(value=(date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
            ttk.Entry(params_frame, textvariable=self.fecha_inicio_var, width=20).grid(row=0, column=1, sticky='ew', padx=(10, 0), pady=5)
            
            # Fecha fin
            ttk.Label(params_frame, text="Fecha Fin:").grid(row=1, column=0, sticky='w', pady=5)
            self.fecha_fin_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
            ttk.Entry(params_frame, textvariable=self.fecha_fin_var, width=20).grid(row=1, column=1, sticky='ew', padx=(10, 0), pady=5)
            
        elif self.tipo_reporte == "Préstamos Próximos a Vencer":
            # Días de adelanto
            ttk.Label(params_frame, text="Días de Adelanto:").grid(row=0, column=0, sticky='w', pady=5)
            self.dias_var = tk.StringVar(value="30")
            ttk.Entry(params_frame, textvariable=self.dias_var, width=10).grid(row=0, column=1, sticky='ew', padx=(10, 0), pady=5)
            
        elif self.tipo_reporte == "Reporte Mensual":
            # Mes y año
            ttk.Label(params_frame, text="Mes:").grid(row=0, column=0, sticky='w', pady=5)
            self.mes_var = tk.StringVar(value=str(date.today().month))
            ttk.Spinbox(params_frame, from_=1, to=12, textvariable=self.mes_var, width=10).grid(row=0, column=1, sticky='ew', padx=(10, 0), pady=5)
            
            ttk.Label(params_frame, text="Año:").grid(row=1, column=0, sticky='w', pady=5)
            self.año_var = tk.StringVar(value=str(date.today().year))
            ttk.Spinbox(params_frame, from_=2020, to=2030, textvariable=self.año_var, width=10).grid(row=1, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Configurar expansión de columnas
        params_frame.columnconfigure(1, weight=1)
        
        # Frame para botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        # Botones
        ttk.Button(button_frame, text="Generar", command=self.generar).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Cancelar", command=self.cancelar).pack(side='right')
        
        # Bind eventos
        self.dialog.bind('<Return>', lambda e: self.generar())
        self.dialog.bind('<Escape>', lambda e: self.cancelar())
    
    def cargar_clientes(self):
        """Cargar lista de clientes"""
        try:
            from src.clientes import ClienteModel
            model = ClienteModel()
            clientes = model.listar_clientes()
            self.clientes_data = [(c[0], c[1]) for c in clientes]
            self.cliente_combo['values'] = [f"{c[0]} - {c[1]}" for c in self.clientes_data]
        except Exception as e:
            print(f"Error al cargar clientes: {e}")
            self.clientes_data = []
    
    def generar(self):
        """Generar reporte"""
        try:
            if self.tipo_reporte == "Estado de Cuenta":
                cliente_seleccionado = self.cliente_var.get()
                if not cliente_seleccionado:
                    messagebox.showerror("Error", "Debes seleccionar un cliente", parent=self.dialog)
                    return
                
                # Obtener ID del cliente
                cliente_id = None
                for cliente in self.clientes_data:
                    if f"{cliente[0]} - {cliente[1]}" == cliente_seleccionado:
                        cliente_id = cliente[0]
                        break
                
                self.result = {'tipo': 'estado_cuenta', 'cliente_id': cliente_id}
                
            elif self.tipo_reporte == "Resumen de Ingresos":
                fecha_inicio = self.fecha_inicio_var.get()
                fecha_fin = self.fecha_fin_var.get()
                
                # Validar fechas
                try:
                    datetime.strptime(fecha_inicio, '%Y-%m-%d')
                    datetime.strptime(fecha_fin, '%Y-%m-%d')
                except ValueError:
                    messagebox.showerror("Error", "Formato de fecha inválido (YYYY-MM-DD)", parent=self.dialog)
                    return
                
                self.result = {
                    'tipo': 'resumen_ingresos', 
                    'fecha_inicio': fecha_inicio, 
                    'fecha_fin': fecha_fin
                }
                
            elif self.tipo_reporte == "Préstamos Próximos a Vencer":
                dias = int(self.dias_var.get())
                if dias <= 0:
                    messagebox.showerror("Error", "Los días deben ser mayores a 0", parent=self.dialog)
                    return
                
                self.result = {'tipo': 'prestamos_proximos', 'dias': dias}
                
            elif self.tipo_reporte == "Reporte Mensual":
                mes = int(self.mes_var.get())
                año = int(self.año_var.get())
                
                if mes < 1 or mes > 12:
                    messagebox.showerror("Error", "Mes inválido", parent=self.dialog)
                    return
                
                self.result = {'tipo': 'reporte_mensual', 'mes': mes, 'año': año}
            
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Dato inválido: {e}", parent=self.dialog)
    
    def cancelar(self):
        """Cancelar operación"""
        self.result = None
        self.dialog.destroy()

class ReportesWindow(ttk.Frame):
    """Ventana principal de reportes"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # Inicializar modelo
        self.model = ReporteManager()
        
        # Crear interfaz
        self.crear_widgets()
    
    def crear_widgets(self):
        """Crear widgets de la interfaz"""
        # Frame principal
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Título
        ttk.Label(main_frame, text="📊 Reportes y Estadísticas", font=('Arial', 16, 'bold')).pack(pady=(0, 20))
        
        # Frame para botones de reportes
        reports_frame = ttk.LabelFrame(main_frame, text="Tipos de Reporte", padding="20")
        reports_frame.pack(fill='x', pady=(0, 20))
        
        # Botones de reportes
        ttk.Button(reports_frame, text="📋 Estado de Cuenta", 
                  command=lambda: self.generar_reporte("Estado de Cuenta")).pack(fill='x', pady=5)
        
        ttk.Button(reports_frame, text="💰 Resumen de Ingresos", 
                  command=lambda: self.generar_reporte("Resumen de Ingresos")).pack(fill='x', pady=5)
        
        ttk.Button(reports_frame, text="⏰ Préstamos Próximos a Vencer", 
                  command=lambda: self.generar_reporte("Préstamos Próximos a Vencer")).pack(fill='x', pady=5)
        
        ttk.Button(reports_frame, text="📅 Reporte Mensual", 
                  command=lambda: self.generar_reporte("Reporte Mensual")).pack(fill='x', pady=5)
        
        # Frame para vista previa
        preview_frame = ttk.LabelFrame(main_frame, text="Vista Previa", padding="10")
        preview_frame.pack(fill='both', expand=True)
        
        # Texto de vista previa
        self.preview_text = tk.Text(preview_frame, height=20, width=80, state='disabled')
        self.preview_text.pack(fill='both', expand=True)
        
        # Scrollbar para vista previa
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient='vertical', command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scrollbar.set)
        preview_scrollbar.pack(side='right', fill='y')
    
    def generar_reporte(self, tipo_reporte: str):
        """Generar reporte específico"""
        try:
            # Abrir diálogo de configuración
            dialog = ReporteDialog(self, tipo_reporte)
            self.wait_window(dialog.dialog)
            
            if not dialog.result:
                return
            
            # Generar reporte según tipo
            if dialog.result['tipo'] == 'estado_cuenta':
                reporte = self.model.generar_estado_cuenta(dialog.result['cliente_id'])
                self.mostrar_estado_cuenta(reporte)
                
            elif dialog.result['tipo'] == 'resumen_ingresos':
                reporte = self.model.generar_resumen_ingresos(
                    dialog.result['fecha_inicio'], 
                    dialog.result['fecha_fin']
                )
                self.mostrar_resumen_ingresos(reporte)
                
            elif dialog.result['tipo'] == 'prestamos_proximos':
                reporte = self.model.obtener_prestamos_proximos_vencer(dialog.result['dias'])
                self.mostrar_prestamos_proximos(reporte)
                
            elif dialog.result['tipo'] == 'reporte_mensual':
                reporte = self.model.generar_reporte_mensual(
                    dialog.result['mes'], 
                    dialog.result['año']
                )
                self.mostrar_reporte_mensual(reporte)
            
            # Preguntar si guardar como archivo
            if messagebox.askyesno("Guardar Reporte", "¿Deseas guardar el reporte como archivo de texto?"):
                self.guardar_reporte(reporte, tipo_reporte)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar reporte: {e}")
    
    def mostrar_estado_cuenta(self, reporte: Dict):
        """Mostrar estado de cuenta en vista previa"""
        cliente = reporte['cliente']
        totales = reporte['totales']
        
        texto = f"""📋 ESTADO DE CUENTA
{'='*50}

👤 CLIENTE:
   Nombre: {cliente['nombre']}
   Teléfono: {cliente['telefono'] or 'No registrado'}
   Dirección: {cliente['direccion'] or 'No registrada'}
   Fecha de registro: {cliente['fecha_registro']}

💰 RESUMEN FINANCIERO:
   Total prestado: ${totales['total_prestado']:,.2f}
   Total pagado: ${totales['total_pagado']:,.2f}
   Saldo pendiente: ${totales['saldo_pendiente']:,.2f}
   Préstamos activos: {totales['prestamos_activos']}

📋 PRÉSTAMOS:
"""
        
        for prestamo in reporte['prestamos']:
            prestamo_id, monto_total, tasa_interes, fecha_inicio, plazo_quincenas, estado, detalles = prestamo
            texto += f"""
   Préstamo #{prestamo_id}:
   - Monto: ${monto_total:,.2f}
   - Tasa: {tasa_interes}% anual
   - Fecha inicio: {fecha_inicio}
   - Plazo: {plazo_quincenas} quincenas
   - Estado: {estado}
   - Detalles: {detalles or 'Sin detalles'}"""
        
        texto += f"\n\n📅 Fecha del reporte: {reporte['fecha_reporte']}"
        
        self.actualizar_vista_previa(texto)
    
    def mostrar_resumen_ingresos(self, reporte: Dict):
        """Mostrar resumen de ingresos en vista previa"""
        periodo = reporte['periodo']
        totales = reporte['totales']
        
        texto = f"""💰 RESUMEN DE INGRESOS
{'='*50}

📅 PERÍODO:
   Desde: {periodo['fecha_inicio']}
   Hasta: {periodo['fecha_fin']}

📊 TOTALES:
   Capital: ${totales['total_capital']:,.2f}
   Interés: ${totales['total_interes']:,.2f}
   Seguro: ${totales['total_seguro']:,.2f}
   TOTAL INGRESOS: ${totales['total_ingresos']:,.2f}

📈 ESTADÍSTICAS:
   Número de pagos: {totales['num_pagos']}
   Clientes activos: {totales['clientes_activos']}

📅 INGRESOS POR DÍA:
"""
        
        for fecha, monto in sorted(reporte['ingresos_por_dia'].items()):
            texto += f"   {fecha}: ${monto:,.2f}\n"
        
        texto += f"\n📅 Fecha del reporte: {reporte['fecha_reporte']}"
        
        self.actualizar_vista_previa(texto)
    
    def mostrar_prestamos_proximos(self, reporte: List[Dict]):
        """Mostrar préstamos próximos a vencer en vista previa"""
        texto = f"""⏰ PRÉSTAMOS PRÓXIMOS A VENCER
{'='*50}

📋 Total de préstamos próximos: {len(reporte)}

"""
        
        for prestamo in reporte:
            texto += f"""💰 Préstamo #{prestamo['prestamo_id']}:
   Cliente: {prestamo['cliente']}
   Teléfono: {prestamo['telefono'] or 'No registrado'}
   Monto total: ${prestamo['monto_total']:,.2f}
   Total pagado: ${prestamo['total_pagado']:,.2f}
   Saldo pendiente: ${prestamo['saldo_pendiente']:,.2f}
   Fecha vencimiento: {prestamo['fecha_vencimiento']}
   Días restantes: {prestamo['dias_restantes']}
   Plazo: {prestamo['plazo_quincenas']} quincenas
   Tasa: {prestamo['tasa_interes']}% anual

"""
        
        texto += f"📅 Fecha del reporte: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self.actualizar_vista_previa(texto)
    
    def mostrar_reporte_mensual(self, reporte: Dict):
        """Mostrar reporte mensual en vista previa"""
        periodo = reporte['periodo']
        estadisticas = reporte['estadisticas']
        ingresos = reporte['ingresos']['totales']
        
        texto = f"""📅 REPORTE MENSUAL
{'='*50}

📅 PERÍODO: {periodo['mes']}/{periodo['año']}

💰 INGRESOS:
   Capital: ${ingresos['total_capital']:,.2f}
   Interés: ${ingresos['total_interes']:,.2f}
   Seguro: ${ingresos['total_seguro']:,.2f}
   TOTAL: ${ingresos['total_ingresos']:,.2f}

📊 ESTADÍSTICAS:
   Nuevos préstamos: {estadisticas['nuevos_prestamos']}
   Monto nuevos préstamos: ${estadisticas['monto_nuevos_prestamos']:,.2f}
   Préstamos pagados: {estadisticas['prestamos_pagados']}
   Clientes activos: {estadisticas['clientes_activos']}

⏰ PRÉSTAMOS PRÓXIMOS A VENCER: {len(reporte['prestamos_proximos'])}

"""
        
        # Mostrar primeros 5 préstamos próximos
        for i, prestamo in enumerate(reporte['prestamos_proximos'][:5]):
            texto += f"   {i+1}. {prestamo['cliente']} - ${prestamo['saldo_pendiente']:,.2f} ({prestamo['dias_restantes']} días)\n"
        
        if len(reporte['prestamos_proximos']) > 5:
            texto += f"   ... y {len(reporte['prestamos_proximos']) - 5} más\n"
        
        texto += f"\n📅 Fecha del reporte: {reporte['fecha_reporte']}"
        
        self.actualizar_vista_previa(texto)
    
    def actualizar_vista_previa(self, texto: str):
        """Actualizar texto de vista previa"""
        self.preview_text.config(state='normal')
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.insert('1.0', texto)
        self.preview_text.config(state='disabled')
    
    def guardar_reporte(self, reporte: Dict, tipo_reporte: str):
        """Guardar reporte como archivo de texto"""
        try:
            # Obtener ruta de guardado
            ruta = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")],
                title=f"Guardar {tipo_reporte}"
            )
            
            if ruta:
                # Obtener texto actual de la vista previa
                texto = self.preview_text.get('1.0', tk.END)
                
                # Guardar archivo
                with open(ruta, 'w', encoding='utf-8') as f:
                    f.write(texto)
                
                messagebox.showinfo("Éxito", f"Reporte guardado en:\n{ruta}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar reporte: {e}")

# Funciones de conveniencia
def generar_estado_cuenta(cliente_id: int) -> Dict:
    """Función de conveniencia para generar estado de cuenta"""
    manager = ReporteManager()
    return manager.generar_estado_cuenta(cliente_id)

def generar_resumen_ingresos(fecha_inicio: str, fecha_fin: str) -> Dict:
    """Función de conveniencia para generar resumen de ingresos"""
    manager = ReporteManager()
    return manager.generar_resumen_ingresos(fecha_inicio, fecha_fin)

def obtener_prestamos_proximos_vencer(dias_adelanto: int = 30) -> List[Dict]:
    """Función de conveniencia para obtener préstamos próximos a vencer"""
    manager = ReporteManager()
    return manager.obtener_prestamos_proximos_vencer(dias_adelanto)
