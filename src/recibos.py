"""
Módulo para la generación de recibos
Funciones para crear y generar recibos de pago en formato PDF
"""

import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional
from fpdf import FPDF
import os

class ReciboManager:
    def __init__(self, db_path: str = '../database/prestamos.db'):
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtener conexión a la base de datos"""
        return sqlite3.connect(self.db_path)
    
    def generar_recibo_pago(self, pago_id: int, ruta_guardado: str = None) -> str:
        """
        Generar un recibo de pago en formato PDF
        
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
            
            # Crear PDF
            pdf = FPDF()
            pdf.add_page()
            
            # Configurar fuente
            pdf.set_font('Arial', 'B', 16)
            
            # Título
            pdf.cell(0, 10, 'RECIBO DE PAGO', 0, 1, 'C')
            pdf.ln(5)
            
            # Información del recibo
            pdf.set_font('Arial', '', 12)
            
            # Número de recibo
            pdf.cell(0, 8, f'Recibo N°: {pago_id:06d}', 0, 1)
            pdf.cell(0, 8, f'Fecha: {pago_info["fecha_pago"]}', 0, 1)
            pdf.ln(5)
            
            # Información del cliente
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'DATOS DEL CLIENTE:', 0, 1)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, f'Nombre: {pago_info["nombre_cliente"]} {pago_info["apellido_cliente"]}', 0, 1)
            pdf.ln(5)
            
            # Información del préstamo
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'DATOS DEL PRÉSTAMO:', 0, 1)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, f'Préstamo N°: {pago_info["prestamo_id"]:06d}', 0, 1)
            pdf.cell(0, 8, f'Monto del préstamo: ${pago_info["monto_prestamo"]:,.2f}', 0, 1)
            pdf.ln(5)
            
            # Información del pago
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'DETALLE DEL PAGO:', 0, 1)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, f'Tipo de pago: {pago_info["tipo_pago"]}', 0, 1)
            pdf.cell(0, 8, f'Monto pagado: ${pago_info["monto_pago"]:,.2f}', 0, 1)
            pdf.ln(5)
            
            # Saldo pendiente
            saldo_pendiente = self.calcular_saldo_pendiente(pago_info["prestamo_id"])
            pdf.cell(0, 8, f'Saldo pendiente: ${saldo_pendiente:,.2f}', 0, 1)
            pdf.ln(10)
            
            # Línea de firma
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.cell(0, 8, 'Firma del cliente', 0, 1, 'C')
            
            # Generar nombre del archivo
            if ruta_guardado is None:
                ruta_guardado = 'recibos'
            
            if not os.path.exists(ruta_guardado):
                os.makedirs(ruta_guardado)
            
            nombre_archivo = f'recibo_{pago_id:06d}_{pago_info["fecha_pago"].replace("-", "")}.pdf'
            ruta_completa = os.path.join(ruta_guardado, nombre_archivo)
            
            # Guardar PDF
            pdf.output(ruta_completa)
            
            return ruta_completa
        except Exception as e:
            raise Exception(f"Error al generar recibo: {e}")
    
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
                    SELECT p.id, p.prestamo_id, p.monto, p.fecha_pago, p.tipo_pago,
                           pr.monto as monto_prestamo, pr.tasa_interes, pr.plazo_meses,
                           c.nombre, c.apellido, c.telefono, c.direccion
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
                        'monto_pago': row[2],
                        'fecha_pago': row[3],
                        'tipo_pago': row[4],
                        'monto_prestamo': row[5],
                        'tasa_interes': row[6],
                        'plazo_meses': row[7],
                        'nombre_cliente': row[8],
                        'apellido_cliente': row[9],
                        'telefono_cliente': row[10],
                        'direccion_cliente': row[11]
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
