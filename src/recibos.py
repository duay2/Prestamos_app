"""
Módulo para la generación de recibos
Funciones para crear y generar recibos de pago en formato PDF
"""

import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional
from fpdf import FPDF
import os

def get_db_path():
    """Obtener la ruta absoluta de la base de datos"""
    # Obtener el directorio base del proyecto (un nivel arriba de src)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_dir = os.path.join(base_dir, 'database')
    db_path = os.path.join(db_dir, 'prestamos.db')
    return db_path

class ReciboManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = get_db_path()
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtener conexión a la base de datos"""
        return sqlite3.connect(self.db_path)
    
    def generar_recibo_pago_individual(self, pago_id: int, ruta_guardado: str = None) -> str:
        """
        Generar un recibo de pago individual recortable en formato PDF
        Formato pequeño tipo tarjeta que se puede recortar y entregar al cliente
        
        Args:
            pago_id: ID del pago
            ruta_guardado: Ruta donde guardar el PDF (opcional)
        
        Returns:
            str: Ruta del archivo PDF generado
        """
        try:
            # Obtener información del pago
            pago_info = self.obtener_info_pago(pago_id)
            if not pago_info:
                raise Exception("Pago no encontrado")
            
            # Calcular saldo pendiente
            from src.pagos import PagoManager
            pago_manager = PagoManager()
            saldo_pendiente = pago_manager.calcular_saldo_pendiente(pago_info["prestamo_id"])
            
            # Crear PDF con formato pequeño (tamaño tarjeta)
            pdf = FPDF(orientation='P', unit='mm', format=(105, 148))  # Tamaño tarjeta (A6)
            pdf.add_page()
            
            # Configurar márgenes pequeños
            pdf.set_margins(5, 5, 5)
            
            # Título
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 8, 'RECIBO DE PAGO', 0, 1, 'C')
            pdf.ln(2)
            
            # Línea separadora
            pdf.line(5, pdf.get_y(), 100, pdf.get_y())
            pdf.ln(3)
            
            # Información del recibo
            pdf.set_font('Arial', '', 9)
            pdf.cell(0, 5, f'Recibo N°: {pago_id:06d}', 0, 1)
            pdf.cell(0, 5, f'Fecha: {pago_info["fecha_pago"]}', 0, 1)
            pdf.ln(2)
            
            # Información del cliente
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 6, 'CLIENTE:', 0, 1)
            pdf.set_font('Arial', '', 9)
            pdf.cell(0, 5, f'{pago_info["nombre_cliente"]}', 0, 1)
            if pago_info.get('telefono_cliente'):
                pdf.cell(0, 5, f'Tel: {pago_info["telefono_cliente"]}', 0, 1)
            pdf.ln(2)
            
            # Información del préstamo
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 6, 'PRESTAMO:', 0, 1)
            pdf.set_font('Arial', '', 9)
            pdf.cell(0, 5, f'No. {pago_info["prestamo_id"]:06d}', 0, 1)
            pdf.cell(0, 5, f'Quincena: {pago_info["numero_quincena"]}/{pago_info["plazo_quincenas"]}', 0, 1)
            pdf.ln(2)
            
            # Detalle del pago
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 6, 'DETALLE DEL PAGO:', 0, 1)
            pdf.set_font('Arial', '', 9)
            pdf.cell(0, 5, f'Monto pagado: ${pago_info["monto_pago"]:,.2f}', 0, 1)
            pdf.ln(2)
            
            # Saldo pendiente
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 6, f'Saldo pendiente: ${saldo_pendiente:,.2f}', 0, 1)
            pdf.ln(3)
            
            # Línea separadora
            pdf.line(5, pdf.get_y(), 100, pdf.get_y())
            pdf.ln(3)
            
            # Firma
            pdf.set_font('Arial', '', 8)
            pdf.cell(0, 5, 'Recibido por:', 0, 1)
            pdf.cell(0, 5, pago_info.get('recibido_por', '_________________'), 0, 1)
            pdf.ln(2)
            pdf.cell(0, 5, 'Firma del cliente:', 0, 1)
            pdf.line(5, pdf.get_y(), 50, pdf.get_y())
            pdf.ln(5)
            
            # Generar nombre del archivo
            if ruta_guardado is None:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ruta_guardado = os.path.join(base_dir, 'recibos')
            
            if not os.path.exists(ruta_guardado):
                os.makedirs(ruta_guardado)
            
            nombre_archivo = f'recibo_{pago_id:06d}_{pago_info["fecha_pago"].replace("-", "")}.pdf'
            ruta_completa = os.path.join(ruta_guardado, nombre_archivo)
            
            # Guardar PDF
            pdf.output(ruta_completa)
            
            return ruta_completa
        except Exception as e:
            raise Exception(f"Error al generar recibo: {e}")
    
    def generar_recibo_pago(self, pago_id: int, ruta_guardado: str = None) -> str:
        """
        Generar un recibo de pago en formato PDF (método legacy, usa el individual)
        
        Args:
            pago_id: ID del pago
            ruta_guardado: Ruta donde guardar el PDF (opcional)
        
        Returns:
            str: Ruta del archivo PDF generado
        """
        return self.generar_recibo_pago_individual(pago_id, ruta_guardado)
    
    def obtener_info_pago(self, pago_id: int) -> Optional[Dict]:
        """
        Obtener información completa de un pago para el recibo
        
        Args:
            pago_id: ID del pago
        
        Returns:
            Dict con la información del pago
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.id, p.prestamo_id, p.numero_quincena, p.fecha_pago,
                           p.monto_capital, p.monto_interes, p.monto_seguro, p.recibido_por,
                           pr.monto_total, pr.plazo_quincenas, pr.tasa_interes, pr.fecha_inicio,
                           c.nombre, c.telefono
                    FROM pagos p
                    JOIN prestamos pr ON p.prestamo_id = pr.id
                    JOIN clientes c ON pr.cliente_id = c.id
                    WHERE p.id = ?
                ''', (pago_id,))
                
                row = cursor.fetchone()
                if row:
                    monto_total = row[4] + row[5] + row[6]  # capital + interes + seguro
                    return {
                        'id': row[0],
                        'prestamo_id': row[1],
                        'numero_quincena': row[2],
                        'fecha_pago': row[3],
                        'monto_capital': row[4],
                        'monto_interes': row[5],
                        'monto_seguro': row[6],
                        'monto_pago': monto_total,
                        'recibido_por': row[7],
                        'monto_prestamo': row[8],
                        'plazo_quincenas': row[9],
                        'tasa_interes': row[10],
                        'fecha_inicio': row[11],
                        'nombre_cliente': row[12],
                        'telefono_cliente': row[13] if len(row) > 13 else None
                    }
                return None
        except sqlite3.Error as e:
            raise Exception(f"Error al obtener información del pago: {e}")
    
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
                
                # Obtener monto del préstamo
                cursor.execute('SELECT monto FROM prestamos WHERE id = ?', (prestamo_id,))
                row = cursor.fetchone()
                if not row:
                    raise Exception("Préstamo no encontrado")
                
                monto_prestamo = row[0]
                
                # Obtener total de pagos realizados
                cursor.execute('''
                    SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE prestamo_id = ?
                ''', (prestamo_id,))
                total_pagado = cursor.fetchone()[0]
                
                saldo_pendiente = monto_prestamo - total_pagado
                return max(0, round(saldo_pendiente, 2))
        except sqlite3.Error as e:
            raise Exception(f"Error al calcular saldo pendiente: {e}")
    
    def generar_recibo_detallado(self, prestamo_id: int, ruta_guardado: str = None) -> str:
        """
        Generar un recibo detallado con historial de pagos
        
        Args:
            prestamo_id: ID del préstamo
            ruta_guardado: Ruta donde guardar el PDF (opcional)
        
        Returns:
            str: Ruta del archivo PDF generado
        """
        try:
            # Obtener información del préstamo
            prestamo_info = self.obtener_info_prestamo(prestamo_id)
            if not prestamo_info:
                raise Exception("Préstamo no encontrado")
            
            # Obtener historial de pagos
            historial_pagos = self.obtener_historial_pagos(prestamo_id)
            
            # Crear PDF
            pdf = FPDF()
            pdf.add_page()
            
            # Configurar fuente
            pdf.set_font('Arial', 'B', 16)
            
            # Título
            pdf.cell(0, 10, 'RECIBO DETALLADO DE PRÉSTAMO', 0, 1, 'C')
            pdf.ln(5)
            
            # Información del préstamo
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'INFORMACIÓN DEL PRÉSTAMO:', 0, 1)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, f'Préstamo N°: {prestamo_id:06d}', 0, 1)
            pdf.cell(0, 8, f'Cliente: {prestamo_info["nombre_cliente"]} {prestamo_info["apellido_cliente"]}', 0, 1)
            pdf.cell(0, 8, f'Monto: ${prestamo_info["monto"]:,.2f}', 0, 1)
            pdf.cell(0, 8, f'Tasa de interés: {prestamo_info["tasa_interes"]}% anual', 0, 1)
            pdf.cell(0, 8, f'Plazo: {prestamo_info["plazo_meses"]} meses', 0, 1)
            pdf.cell(0, 8, f'Fecha de inicio: {prestamo_info["fecha_inicio"]}', 0, 1)
            pdf.cell(0, 8, f'Estado: {prestamo_info["estado"]}', 0, 1)
            pdf.ln(5)
            
            # Historial de pagos
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'HISTORIAL DE PAGOS:', 0, 1)
            pdf.ln(5)
            
            # Encabezados de tabla
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(40, 8, 'Fecha', 1)
            pdf.cell(30, 8, 'Monto', 1)
            pdf.cell(30, 8, 'Tipo', 1)
            pdf.cell(40, 8, 'Saldo Restante', 1)
            pdf.ln()
            
            # Datos de la tabla
            pdf.set_font('Arial', '', 10)
            for pago in historial_pagos:
                pdf.cell(40, 8, pago['fecha_pago'], 1)
                pdf.cell(30, 8, f"${pago['monto_pago']:,.2f}", 1)
                pdf.cell(30, 8, pago['tipo_pago'], 1)
                pdf.cell(40, 8, f"${pago['saldo_restante']:,.2f}", 1)
                pdf.ln()
            
            pdf.ln(10)
            
            # Resumen
            total_pagado = sum(pago['monto_pago'] for pago in historial_pagos)
            saldo_pendiente = prestamo_info['monto'] - total_pagado
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'RESUMEN:', 0, 1)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, f'Total pagado: ${total_pagado:,.2f}', 0, 1)
            pdf.cell(0, 8, f'Saldo pendiente: ${max(0, saldo_pendiente):,.2f}', 0, 1)
            
            # Generar nombre del archivo
            if ruta_guardado is None:
                ruta_guardado = 'recibos'
            
            if not os.path.exists(ruta_guardado):
                os.makedirs(ruta_guardado)
            
            nombre_archivo = f'recibo_detallado_{prestamo_id:06d}_{date.today().strftime("%Y%m%d")}.pdf'
            ruta_completa = os.path.join(ruta_guardado, nombre_archivo)
            
            # Guardar PDF
            pdf.output(ruta_completa)
            
            return ruta_completa
        except Exception as e:
            raise Exception(f"Error al generar recibo detallado: {e}")
    
    def obtener_info_prestamo(self, prestamo_id: int) -> Optional[Dict]:
        """
        Obtener información completa de un préstamo
        
        Args:
            prestamo_id: ID del préstamo
        
        Returns:
            Dict con la información del préstamo
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.id, p.monto, p.tasa_interes, p.plazo_meses, p.fecha_inicio, p.estado,
                           c.nombre, c.apellido, c.telefono, c.direccion
                    FROM prestamos p
                    JOIN clientes c ON p.cliente_id = c.id
                    WHERE p.id = ?
                ''', (prestamo_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'monto': row[1],
                        'tasa_interes': row[2],
                        'plazo_meses': row[3],
                        'fecha_inicio': row[4],
                        'estado': row[5],
                        'nombre_cliente': row[6],
                        'apellido_cliente': row[7],
                        'telefono_cliente': row[8],
                        'direccion_cliente': row[9]
                    }
                return None
        except sqlite3.Error as e:
            raise Exception(f"Error al obtener información del préstamo: {e}")
    
    def obtener_historial_pagos(self, prestamo_id: int) -> List[Dict]:
        """
        Obtener el historial de pagos de un préstamo
        
        Args:
            prestamo_id: ID del préstamo
        
        Returns:
            Lista de diccionarios con el historial de pagos
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Obtener información del préstamo
                cursor.execute('SELECT monto FROM prestamos WHERE id = ?', (prestamo_id,))
                row = cursor.fetchone()
                if not row:
                    raise Exception("Préstamo no encontrado")
                
                monto_prestamo = row[0]
                
                # Obtener todos los pagos
                cursor.execute('''
                    SELECT monto, fecha_pago, tipo_pago
                    FROM pagos 
                    WHERE prestamo_id = ?
                    ORDER BY fecha_pago
                ''', (prestamo_id,))
                
                pagos = cursor.fetchall()
                
                # Calcular saldo acumulado
                saldo_acumulado = monto_prestamo
                historial = []
                
                for pago in pagos:
                    monto_pago, fecha_pago, tipo_pago = pago
                    saldo_acumulado -= monto_pago
                    
                    historial.append({
                        'fecha_pago': fecha_pago,
                        'monto_pago': monto_pago,
                        'tipo_pago': tipo_pago,
                        'saldo_restante': max(0, round(saldo_acumulado, 2))
                    })
                
                return historial
        except sqlite3.Error as e:
            raise Exception(f"Error al obtener historial de pagos: {e}")
    
    def generar_recibo_mensual(self, prestamo_id: int, mes: int, año: int, ruta_guardado: str = None) -> str:
        """
        Generar un recibo mensual con el resumen de pagos del mes
        
        Args:
            prestamo_id: ID del préstamo
            mes: Mes (1-12)
            año: Año
            ruta_guardado: Ruta donde guardar el PDF (opcional)
        
        Returns:
            str: Ruta del archivo PDF generado
        """
        try:
            # Obtener información del préstamo
            prestamo_info = self.obtener_info_prestamo(prestamo_id)
            if not prestamo_info:
                raise Exception("Préstamo no encontrado")
            
            # Obtener pagos del mes
            pagos_mes = self.obtener_pagos_mes(prestamo_id, mes, año)
            
            # Crear PDF
            pdf = FPDF()
            pdf.add_page()
            
            # Configurar fuente
            pdf.set_font('Arial', 'B', 16)
            
            # Título
            pdf.cell(0, 10, 'RECIBO MENSUAL', 0, 1, 'C')
            pdf.ln(5)
            
            # Información del período
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, f'Período: {mes:02d}/{año}', 0, 1)
            pdf.ln(5)
            
            # Información del cliente
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'DATOS DEL CLIENTE:', 0, 1)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, f'Nombre: {prestamo_info["nombre_cliente"]} {prestamo_info["apellido_cliente"]}', 0, 1)
            pdf.cell(0, 8, f'Préstamo N°: {prestamo_id:06d}', 0, 1)
            pdf.ln(5)
            
            # Pagos del mes
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'PAGOS REALIZADOS EN EL MES:', 0, 1)
            pdf.ln(5)
            
            if pagos_mes:
                # Encabezados de tabla
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(40, 8, 'Fecha', 1)
                pdf.cell(40, 8, 'Monto', 1)
                pdf.cell(40, 8, 'Tipo', 1)
                pdf.ln()
                
                # Datos de la tabla
                pdf.set_font('Arial', '', 10)
                total_mes = 0
                for pago in pagos_mes:
                    pdf.cell(40, 8, pago['fecha_pago'], 1)
                    pdf.cell(40, 8, f"${pago['monto']:,.2f}", 1)
                    pdf.cell(40, 8, pago['tipo_pago'], 1)
                    pdf.ln()
                    total_mes += pago['monto']
                
                pdf.ln(5)
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 8, f'Total del mes: ${total_mes:,.2f}', 0, 1)
            else:
                pdf.set_font('Arial', '', 12)
                pdf.cell(0, 8, 'No se realizaron pagos en este mes', 0, 1)
            
            pdf.ln(10)
            
            # Saldo pendiente
            saldo_pendiente = self.calcular_saldo_pendiente(prestamo_id)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, f'Saldo pendiente: ${saldo_pendiente:,.2f}', 0, 1)
            
            # Generar nombre del archivo
            if ruta_guardado is None:
                ruta_guardado = 'recibos'
            
            if not os.path.exists(ruta_guardado):
                os.makedirs(ruta_guardado)
            
            nombre_archivo = f'recibo_mensual_{prestamo_id:06d}_{año}{mes:02d}.pdf'
            ruta_completa = os.path.join(ruta_guardado, nombre_archivo)
            
            # Guardar PDF
            pdf.output(ruta_completa)
            
            return ruta_completa
        except Exception as e:
            raise Exception(f"Error al generar recibo mensual: {e}")
    
    def obtener_pagos_mes(self, prestamo_id: int, mes: int, año: int) -> List[Dict]:
        """
        Obtener los pagos realizados en un mes específico
        
        Args:
            prestamo_id: ID del préstamo
            mes: Mes (1-12)
            año: Año
        
        Returns:
            Lista de pagos del mes
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                fecha_inicio = f"{año}-{mes:02d}-01"
                if mes == 12:
                    fecha_fin = f"{año + 1}-01-01"
                else:
                    fecha_fin = f"{año}-{mes + 1:02d}-01"
                
                cursor.execute('''
                    SELECT monto, fecha_pago, tipo_pago
                    FROM pagos 
                    WHERE prestamo_id = ? AND fecha_pago >= ? AND fecha_pago < ?
                    ORDER BY fecha_pago
                ''', (prestamo_id, fecha_inicio, fecha_fin))
                
                pagos = cursor.fetchall()
                return [
                    {
                        'monto': pago[0],
                        'fecha_pago': pago[1],
                        'tipo_pago': pago[2]
                    }
                    for pago in pagos
                ]
        except sqlite3.Error as e:
            raise Exception(f"Error al obtener pagos del mes: {e}")

    def generar_recibo_cliente_formato_capta(self, cliente_id: int, fecha_pago: str = None, ruta_guardado: str = None) -> str:
        """
        Generar recibo en formato similar a CAPTA VALE para un cliente
        Incluye todos los préstamos activos del cliente
        
        Args:
            cliente_id: ID del cliente
            fecha_pago: Fecha del pago (opcional, usa fecha actual si no se proporciona)
            ruta_guardado: Ruta donde guardar el PDF (opcional)
        
        Returns:
            str: Ruta del archivo PDF generado
        """
        try:
            from src.pagos import PagoManager
            from src.config import cargar_configuracion
            from datetime import date, datetime
            
            pago_manager = PagoManager()
            config = cargar_configuracion()
            nombre_prestamista = config.get('prestamista_nombre', 'CAPTA VALE')
            
            # Obtener información del cliente
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, nombre, telefono FROM clientes WHERE id = ?', (cliente_id,))
                cliente_row = cursor.fetchone()
                if not cliente_row:
                    raise Exception("Cliente no encontrado")
                
                cliente_id_db, nombre_cliente, telefono_cliente = cliente_row
            
            # Obtener préstamos activos del cliente
            prestamos_activos = pago_manager.obtener_pagos_pendientes(cliente_id=cliente_id)
            
            if not prestamos_activos:
                raise Exception("El cliente no tiene préstamos activos")
            
            # Usar fecha proporcionada o fecha actual
            if fecha_pago is None:
                fecha_pago = date.today().strftime('%d/%m/%Y')
            else:
                # Convertir formato si es necesario
                try:
                    fecha_obj = datetime.strptime(fecha_pago, '%Y-%m-%d')
                    fecha_pago = fecha_obj.strftime('%d/%m/%Y')
                except:
                    pass  # Ya está en formato correcto
            
            # Crear PDF
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.add_page()
            pdf.set_margins(15, 15, 15)
            
            # Color verde (RGB: aproximadamente #4CAF50 o similar)
            verde_claro = (76, 175, 80)  # Verde claro para barras
            verde_oscuro = (46, 125, 50)  # Verde oscuro para texto
            
            # Encabezado - Logo y nombre de empresa (simulado)
            pdf.set_font('Arial', 'B', 24)
            pdf.set_text_color(*verde_oscuro)
            pdf.cell(0, 10, nombre_prestamista, 0, 1, 'L')
            pdf.ln(2)
            
            # Información del cliente y fecha
            pdf.set_font('Arial', '', 11)
            pdf.set_text_color(0, 0, 0)  # Negro
            pdf.cell(0, 6, f'CLIENTE: {nombre_cliente.upper()}', 0, 1, 'L')
            
            # Distribuidor (prestamista)
            if nombre_prestamista:
                pdf.cell(0, 6, f'DISTRIBUIDOR(A): {nombre_prestamista.upper()}', 0, 1, 'L')
            
            # Fecha de pago (alineada a la derecha)
            pdf.set_xy(15, pdf.get_y() - 12)
            pdf.cell(0, 6, f'FECHA DE PAGO: {fecha_pago}', 0, 0, 'R')
            pdf.ln(8)
            
            # Tabla de detalles
            # Encabezado de tabla con fondo verde
            y_tabla = pdf.get_y()
            ancho_total = 180  # Ancho total de la página menos márgenes
            alto_encabezado = 8
            
            # Dibujar barra verde del encabezado
            pdf.set_fill_color(*verde_claro)
            pdf.rect(15, y_tabla, ancho_total, alto_encabezado, 'F')
            
            # Texto del encabezado en blanco
            pdf.set_text_color(255, 255, 255)  # Blanco
            pdf.set_font('Arial', 'B', 9)
            
            # Columnas
            ancho_folio = 30
            ancho_fecha = 35
            ancho_num_pago = 30
            ancho_saldo_ant = 30
            ancho_importe = 30
            ancho_nuevo_saldo = 25
            
            x_pos = 15
            pdf.set_xy(x_pos, y_tabla + 2)
            pdf.cell(ancho_folio, 6, 'FOLIO', 0, 0, 'C')
            
            x_pos += ancho_folio
            pdf.set_xy(x_pos, y_tabla + 2)
            pdf.cell(ancho_fecha, 6, 'FECHA DE DISPOSICION', 0, 0, 'C')
            
            x_pos += ancho_fecha
            pdf.set_xy(x_pos, y_tabla + 2)
            pdf.cell(ancho_num_pago, 6, 'NUM. DE PAGO', 0, 0, 'C')
            
            x_pos += ancho_num_pago
            pdf.set_xy(x_pos, y_tabla + 2)
            pdf.cell(ancho_saldo_ant, 6, 'SALDO ANTERIOR', 0, 0, 'C')
            
            x_pos += ancho_saldo_ant
            pdf.set_xy(x_pos, y_tabla + 2)
            pdf.cell(ancho_importe, 6, 'IMPORTE DE PAGO', 0, 0, 'C')
            
            x_pos += ancho_importe
            pdf.set_xy(x_pos, y_tabla + 2)
            pdf.cell(ancho_nuevo_saldo, 6, 'NUEVO SALDO', 0, 0, 'C')
            
            # Filas de datos
            y_fila = y_tabla + alto_encabezado
            pdf.set_text_color(100, 100, 100)  # Gris para datos
            pdf.set_font('Arial', '', 9)
            
            total_saldo_anterior = 0
            total_importe = 0
            total_nuevo_saldo = 0
            
            for prestamo in prestamos_activos:
                # Obtener próxima quincena
                proxima_quincena = pago_manager.obtener_proxima_quincena(prestamo['prestamo_id'])
                
                # Calcular saldos
                saldo_anterior = prestamo['saldo_pendiente']
                importe_pago = prestamo['cuota_quincenal']
                nuevo_saldo = max(0, saldo_anterior - importe_pago)
                
                # Formatear fecha de disposición (fecha de inicio del préstamo)
                try:
                    fecha_disposicion = datetime.strptime(prestamo['fecha_inicio'], '%Y-%m-%d')
                    fecha_disposicion_str = fecha_disposicion.strftime('%d/%m/%Y')
                except:
                    fecha_disposicion_str = prestamo['fecha_inicio']
                
                # Folio (usar ID del préstamo)
                folio = f"D{prestamo['prestamo_id']:06d}"
                
                # Número de pago
                num_pago = f"{proxima_quincena} de {prestamo['plazo_quincenas']}"
                
                # Dibujar fila
                x_pos = 15
                pdf.set_xy(x_pos, y_fila + 2)
                pdf.cell(ancho_folio, 6, folio, 0, 0, 'C')
                
                x_pos += ancho_folio
                pdf.set_xy(x_pos, y_fila + 2)
                pdf.cell(ancho_fecha, 6, fecha_disposicion_str, 0, 0, 'C')
                
                x_pos += ancho_fecha
                pdf.set_xy(x_pos, y_fila + 2)
                pdf.cell(ancho_num_pago, 6, num_pago, 0, 0, 'C')
                
                x_pos += ancho_num_pago
                pdf.set_xy(x_pos, y_fila + 2)
                pdf.cell(ancho_saldo_ant, 6, f"${saldo_anterior:,.2f}", 0, 0, 'R')
                
                x_pos += ancho_saldo_ant
                pdf.set_xy(x_pos, y_fila + 2)
                pdf.cell(ancho_importe, 6, f"${importe_pago:,.2f}", 0, 0, 'R')
                
                x_pos += ancho_importe
                pdf.set_xy(x_pos, y_fila + 2)
                pdf.cell(ancho_nuevo_saldo, 6, f"${nuevo_saldo:,.2f}", 0, 0, 'R')
                
                # Acumular totales
                total_saldo_anterior += saldo_anterior
                total_importe += importe_pago
                total_nuevo_saldo += nuevo_saldo
                
                y_fila += 8  # Espacio entre filas
            
            # Pie de página con totales
            y_pie = y_fila + 2
            pdf.set_fill_color(*verde_claro)
            pdf.rect(15, y_pie, ancho_total, alto_encabezado, 'F')
            
            # Texto de totales en blanco
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Arial', 'B', 10)
            pdf.set_xy(15, y_pie + 2)
            pdf.cell(ancho_folio + ancho_fecha + ancho_num_pago, 6, 'TOTALES:', 0, 0, 'L')
            
            # Totales numéricos
            x_pos = 15 + ancho_folio + ancho_fecha + ancho_num_pago
            pdf.set_xy(x_pos, y_pie + 2)
            pdf.cell(ancho_saldo_ant, 6, f"${total_saldo_anterior:,.2f}", 0, 0, 'R')
            
            x_pos += ancho_saldo_ant
            pdf.set_xy(x_pos, y_pie + 2)
            pdf.cell(ancho_importe, 6, f"${total_importe:,.2f}", 0, 0, 'R')
            
            x_pos += ancho_importe
            pdf.set_xy(x_pos, y_pie + 2)
            pdf.cell(ancho_nuevo_saldo, 6, f"${total_nuevo_saldo:,.2f}", 0, 0, 'R')
            
            # Generar nombre del archivo
            if ruta_guardado is None:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ruta_guardado = os.path.join(base_dir, 'recibos')
            
            if not os.path.exists(ruta_guardado):
                os.makedirs(ruta_guardado)
            
            fecha_archivo = date.today().strftime("%Y%m%d")
            nombre_archivo = f'recibo_{nombre_cliente.replace(" ", "_")}_{fecha_archivo}.pdf'
            ruta_completa = os.path.join(ruta_guardado, nombre_archivo)
            
            # Guardar PDF
            pdf.output(ruta_completa)
            
            return ruta_completa
        except Exception as e:
            raise Exception(f"Error al generar recibo: {e}")
    
    def generar_hoja_recibos_activos(self, ruta_guardado: str = None) -> str:
        """
        Generar una hoja con recibos de todos los préstamos activos
        Formato CAPTA VALE en cuadrícula 2x2 (o más) para imprimir y recortar
        
        Args:
            ruta_guardado: Ruta donde guardar el PDF (opcional)
        
        Returns:
            str: Ruta del archivo PDF generado
        """
        try:
            from src.pagos import PagoManager
            from src.config import cargar_configuracion
            from datetime import date, datetime
            
            pago_manager = PagoManager()
            config = cargar_configuracion()
            nombre_prestamista = config.get('prestamista_nombre', 'CAPTA VALE')
            
            # Obtener todos los préstamos activos agrupados por cliente
            prestamos_activos = pago_manager.obtener_pagos_pendientes()
            
            if not prestamos_activos:
                raise Exception("No hay préstamos activos para generar recibos")
            
            # Agrupar préstamos por cliente
            prestamos_por_cliente = {}
            for prestamo in prestamos_activos:
                cliente_id = prestamo['cliente_id']
                if cliente_id not in prestamos_por_cliente:
                    prestamos_por_cliente[cliente_id] = {
                        'cliente_id': cliente_id,
                        'nombre_cliente': prestamo['nombre_cliente'],
                        'prestamos': []
                    }
                prestamos_por_cliente[cliente_id]['prestamos'].append(prestamo)
            
            # Crear PDF tamaño A4
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.set_margins(10, 10, 10)
            
            # Tamaño de cada recibo (para cuadrícula 2x2)
            ancho_recibo = 90
            alto_recibo = 70  # Tamaño original
            recibos_por_fila = 2
            recibos_por_columna = 2
            espacio_vertical = 5
            espacio_horizontal = 5
            
            # Colores
            verde_claro = (76, 175, 80)
            verde_oscuro = (46, 125, 50)
            
            recibos_generados = 0
            y_inicial = 10
            x_inicial = 10
            fecha_pago = date.today().strftime('%d/%m/%Y')
            
            # Agregar la primera página
            pdf.add_page()
            
            # Generar un recibo por cada cliente (con todos sus préstamos)
            for cliente_id, datos_cliente in prestamos_por_cliente.items():
                # Si necesitamos una nueva página
                if recibos_generados > 0 and recibos_generados % (recibos_por_fila * recibos_por_columna) == 0:
                    pdf.add_page()
                
                # Calcular posición del recibo en la página actual
                recibos_en_pagina = recibos_generados % (recibos_por_fila * recibos_por_columna)
                fila = recibos_en_pagina // recibos_por_fila
                columna = recibos_en_pagina % recibos_por_fila
                
                # Calcular coordenadas absolutas
                x = x_inicial + columna * (ancho_recibo + espacio_horizontal)
                y = y_inicial + fila * (alto_recibo + espacio_vertical)
                
                # Dibujar borde del recibo
                pdf.rect(x, y, ancho_recibo, alto_recibo)
                
                # Información del cliente
                y_pos = y + 3
                pdf.set_font('Arial', '', 6)
                pdf.set_text_color(0, 0, 0)
                pdf.set_xy(x + 3, y_pos)
                nombre_cliente = datos_cliente['nombre_cliente'][:35]
                pdf.cell(ancho_recibo - 6, 3, f'CLIENTE: {nombre_cliente.upper()}', 0, 0, 'L')
                
                # Prestamista
                y_pos += 3
                pdf.set_xy(x + 3, y_pos)
                pdf.cell(ancho_recibo - 6, 3, f'PRESTAMISTA: {nombre_prestamista.upper()[:35]}', 0, 0, 'L')
                
                # Fecha de pago (alineada a la derecha)
                pdf.set_xy(x + 3, y + 3)
                pdf.cell(ancho_recibo - 6, 3, f'FECHA DE PAGO: {fecha_pago}', 0, 0, 'R')
                
                # Tabla de detalles
                y_tabla = y + 10
                ancho_tabla = ancho_recibo - 6
                alto_encabezado = 5
                
                # Encabezado de tabla con fondo verde
                pdf.set_fill_color(*verde_claro)
                pdf.rect(x + 3, y_tabla, ancho_tabla, alto_encabezado, 'F')
                
                # Texto del encabezado en blanco
                pdf.set_text_color(255, 255, 255)
                pdf.set_font('Arial', 'B', 5)
                
                # Anchos de columnas (proporcionales)
                ancho_folio = 12
                ancho_fecha = 18
                ancho_num_pago = 12
                ancho_saldo_ant = 15
                ancho_importe = 15
                ancho_nuevo_saldo = 13
                
                x_pos = x + 3
                pdf.set_xy(x_pos, y_tabla + 1)
                pdf.cell(ancho_folio, 3, 'FOLIO', 0, 0, 'C')
                
                x_pos += ancho_folio
                pdf.set_xy(x_pos, y_tabla + 1)
                pdf.cell(ancho_fecha, 3, 'FECHA DISP.', 0, 0, 'C')
                
                x_pos += ancho_fecha
                pdf.set_xy(x_pos, y_tabla + 1)
                pdf.cell(ancho_num_pago, 3, 'NUM.PAGO', 0, 0, 'C')
                
                x_pos += ancho_num_pago
                pdf.set_xy(x_pos, y_tabla + 1)
                pdf.cell(ancho_saldo_ant, 3, 'SALDO ANT.', 0, 0, 'C')
                
                x_pos += ancho_saldo_ant
                pdf.set_xy(x_pos, y_tabla + 1)
                pdf.cell(ancho_importe, 3, 'IMPORTE', 0, 0, 'C')
                
                x_pos += ancho_importe
                pdf.set_xy(x_pos, y_tabla + 1)
                pdf.cell(ancho_nuevo_saldo, 3, 'NUEVO SALDO', 0, 0, 'C')
                
                # Filas de datos
                y_fila = y_tabla + alto_encabezado
                pdf.set_text_color(100, 100, 100)
                pdf.set_font('Arial', '', 5)
                
                total_saldo_anterior = 0
                total_importe = 0
                total_nuevo_saldo = 0
                
                prestamos_cliente = datos_cliente['prestamos']
                for prestamo in prestamos_cliente:
                    # Obtener próxima quincena
                    proxima_quincena = pago_manager.obtener_proxima_quincena(prestamo['prestamo_id'])
                    
                    # Calcular saldos
                    saldo_anterior = prestamo['saldo_pendiente']
                    importe_pago = prestamo['cuota_quincenal']
                    nuevo_saldo = max(0, saldo_anterior - importe_pago)
                    
                    # Formatear fecha de disposición
                    try:
                        fecha_disposicion = datetime.strptime(prestamo['fecha_inicio'], '%Y-%m-%d')
                        fecha_disposicion_str = fecha_disposicion.strftime('%d/%m/%Y')
                    except:
                        fecha_disposicion_str = prestamo['fecha_inicio']
                    
                    # Folio
                    folio = f"D{prestamo['prestamo_id']:06d}"
                    
                    # Número de pago
                    num_pago = f"{proxima_quincena}/{prestamo['plazo_quincenas']}"
                    
                    # Dibujar fila
                    x_pos = x + 3
                    pdf.set_xy(x_pos, y_fila + 1)
                    pdf.cell(ancho_folio, 3, folio, 0, 0, 'C')
                    
                    x_pos += ancho_folio
                    pdf.set_xy(x_pos, y_fila + 1)
                    pdf.cell(ancho_fecha, 3, fecha_disposicion_str, 0, 0, 'C')
                    
                    x_pos += ancho_fecha
                    pdf.set_xy(x_pos, y_fila + 1)
                    pdf.cell(ancho_num_pago, 3, num_pago, 0, 0, 'C')
                    
                    x_pos += ancho_num_pago
                    pdf.set_xy(x_pos, y_fila + 1)
                    pdf.cell(ancho_saldo_ant, 3, f"${saldo_anterior:,.0f}", 0, 0, 'R')
                    
                    x_pos += ancho_saldo_ant
                    pdf.set_xy(x_pos, y_fila + 1)
                    pdf.cell(ancho_importe, 3, f"${importe_pago:,.0f}", 0, 0, 'R')
                    
                    x_pos += ancho_importe
                    pdf.set_xy(x_pos, y_fila + 1)
                    pdf.cell(ancho_nuevo_saldo, 3, f"${nuevo_saldo:,.0f}", 0, 0, 'R')
                    
                    # Acumular totales
                    total_saldo_anterior += saldo_anterior
                    total_importe += importe_pago
                    total_nuevo_saldo += nuevo_saldo
                    
                    y_fila += 4  # Espacio entre filas
                
                # Pie de página con totales
                y_pie = y_fila + 1
                pdf.set_fill_color(*verde_claro)
                pdf.rect(x + 3, y_pie, ancho_tabla, alto_encabezado, 'F')
                
                # Texto de totales en blanco
                pdf.set_text_color(255, 255, 255)
                pdf.set_font('Arial', 'B', 5)
                pdf.set_xy(x + 3, y_pie + 1)
                pdf.cell(ancho_folio + ancho_fecha + ancho_num_pago, 3, 'TOTALES:', 0, 0, 'L')
                
                # Totales numéricos
                x_pos = x + 3 + ancho_folio + ancho_fecha + ancho_num_pago
                pdf.set_xy(x_pos, y_pie + 1)
                pdf.cell(ancho_saldo_ant, 3, f"${total_saldo_anterior:,.0f}", 0, 0, 'R')
                
                x_pos += ancho_saldo_ant
                pdf.set_xy(x_pos, y_pie + 1)
                pdf.cell(ancho_importe, 3, f"${total_importe:,.0f}", 0, 0, 'R')
                
                x_pos += ancho_importe
                pdf.set_xy(x_pos, y_pie + 1)
                pdf.cell(ancho_nuevo_saldo, 3, f"${total_nuevo_saldo:,.0f}", 0, 0, 'R')
                
                recibos_generados += 1
            
            # Generar nombre del archivo
            if ruta_guardado is None:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ruta_guardado = os.path.join(base_dir, 'recibos')
            
            if not os.path.exists(ruta_guardado):
                os.makedirs(ruta_guardado)
            
            fecha_actual = date.today().strftime("%Y%m%d")
            nombre_archivo = f'recibos_activos_{fecha_actual}.pdf'
            ruta_completa = os.path.join(ruta_guardado, nombre_archivo)
            
            # Guardar PDF
            pdf.output(ruta_completa)
            
            return ruta_completa
        except Exception as e:
            raise Exception(f"Error al generar hoja de recibos: {e}")

# Funciones de conveniencia
def generar_recibo_pago(pago_id: int, **kwargs) -> str:
    """Función de conveniencia para generar recibo de pago"""
    manager = ReciboManager()
    return manager.generar_recibo_pago(pago_id, **kwargs)

def generar_recibo_detallado(prestamo_id: int, **kwargs) -> str:
    """Función de conveniencia para generar recibo detallado"""
    manager = ReciboManager()
    return manager.generar_recibo_detallado(prestamo_id, **kwargs)

def generar_recibo_mensual(prestamo_id: int, mes: int, año: int, **kwargs) -> str:
    """Función de conveniencia para generar recibo mensual"""
    manager = ReciboManager()
    return manager.generar_recibo_mensual(prestamo_id, mes, año, **kwargs)
