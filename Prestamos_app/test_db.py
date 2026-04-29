#!/usr/bin/env python3
"""
Script de prueba para verificar la base de datos y los problemas reportados
"""

import sqlite3
from datetime import datetime

def test_database():
    """Probar la base de datos y verificar los problemas"""
    
    print("🔍 VERIFICANDO BASE DE DATOS")
    print("=" * 50)
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect('database/prestamos.db')
        cursor = conn.cursor()
        
        # Verificar clientes
        print("\n👥 CLIENTES:")
        cursor.execute('SELECT * FROM clientes')
        clientes = cursor.fetchall()
        for cliente in clientes:
            print(f"  ID: {cliente[0]}, Nombre: {cliente[1]}, Teléfono: {cliente[2]}")
        
        # Verificar préstamos
        print("\n💰 PRÉSTAMOS:")
        cursor.execute('''
            SELECT p.id, p.cliente_id, c.nombre, p.monto_total, p.tasa_interes, 
                   p.plazo_quincenas, p.fecha_inicio, p.estado
            FROM prestamos p
            JOIN clientes c ON p.cliente_id = c.id
        ''')
        prestamos = cursor.fetchall()
        for prestamo in prestamos:
            print(f"  ID: {prestamo[0]}, Cliente: {prestamo[2]}, Monto: ${prestamo[3]:,.2f}, Estado: {prestamo[7]}")
        
        # Verificar pagos
        print("\n💳 PAGOS:")
        cursor.execute('''
            SELECT p.id, p.prestamo_id, pr.cliente_id, c.nombre, p.fecha_pago, 
                   p.monto_capital, p.monto_interes, p.monto_seguro
            FROM pagos p
            JOIN prestamos pr ON p.prestamo_id = pr.id
            JOIN clientes c ON pr.cliente_id = c.id
        ''')
        pagos = cursor.fetchall()
        for pago in pagos:
            print(f"  ID: {pago[0]}, Préstamo: {pago[1]}, Cliente: {pago[3]}, Fecha: {pago[4]}")
        
        # Verificar préstamos activos por cliente
        print("\n🔍 VERIFICANDO PRÉSTAMOS ACTIVOS POR CLIENTE:")
        for cliente in clientes:
            cliente_id = cliente[0]
            cursor.execute('''
                SELECT COUNT(*) FROM prestamos 
                WHERE cliente_id = ? AND estado = 'ACTIVO'
            ''', (cliente_id,))
            prestamos_activos = cursor.fetchone()[0]
            print(f"  Cliente {cliente[1]} (ID: {cliente_id}): {prestamos_activos} préstamos activos")
        
        # Verificar estructura de tablas
        print("\n📋 ESTRUCTURA DE TABLAS:")
        cursor.execute("PRAGMA table_info(clientes)")
        print("  Tabla clientes:")
        for col in cursor.fetchall():
            print(f"    {col[1]} ({col[2]})")
        
        cursor.execute("PRAGMA table_info(prestamos)")
        print("  Tabla prestamos:")
        for col in cursor.fetchall():
            print(f"    {col[1]} ({col[2]})")
        
        cursor.execute("PRAGMA table_info(pagos)")
        print("  Tabla pagos:")
        for col in cursor.fetchall():
            print(f"    {col[1]} ({col[2]})")
        
        conn.close()
        
        print("\n✅ Verificación completada")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_database()
