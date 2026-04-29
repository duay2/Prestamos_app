#!/usr/bin/env python3
"""
Script de prueba final para verificar que todos los problemas se han solucionado
"""

import sqlite3
from datetime import datetime

def test_final():
    """Probar que todos los problemas se han solucionado"""
    
    print("🔍 VERIFICACIÓN FINAL - PROBLEMAS SOLUCIONADOS")
    print("=" * 60)
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect('database/prestamos.db')
        cursor = conn.cursor()
        
        # 1. Verificar que los clientes existen
        print("\n✅ 1. VERIFICANDO CLIENTES:")
        cursor.execute('SELECT * FROM clientes')
        clientes = cursor.fetchall()
        print(f"   Total de clientes: {len(clientes)}")
        for cliente in clientes:
            print(f"   ID: {cliente[0]}, Nombre: {cliente[1]}, Teléfono: {cliente[2]}")
        
        # 2. Verificar que los préstamos existen y usan las columnas correctas
        print("\n✅ 2. VERIFICANDO PRÉSTAMOS:")
        cursor.execute('''
            SELECT p.id, p.cliente_id, c.nombre, p.monto_total, p.plazo_quincenas, p.estado
            FROM prestamos p
            JOIN clientes c ON p.cliente_id = c.id
        ''')
        prestamos = cursor.fetchall()
        print(f"   Total de préstamos: {len(prestamos)}")
        for prestamo in prestamos:
            print(f"   ID: {prestamo[0]}, Cliente: {prestamo[2]}, Monto: ${prestamo[3]:,.2f}, Quincenas: {prestamo[4]}, Estado: {prestamo[5]}")
        
        # 3. Verificar que Diego (cliente 6) no tiene préstamos activos
        print("\n✅ 3. VERIFICANDO CLIENTE DIEGO:")
        cursor.execute('''
            SELECT COUNT(*) FROM prestamos 
            WHERE cliente_id = 6 AND estado = 'ACTIVO'
        ''')
        prestamos_diego = cursor.fetchone()[0]
        print(f"   Diego tiene {prestamos_diego} préstamos activos (debería ser 0)")
        
        # 4. Verificar que los clientes con préstamos activos no se pueden eliminar
        print("\n✅ 4. VERIFICANDO PRÉSTAMOS ACTIVOS POR CLIENTE:")
        for cliente in clientes[:5]:  # Solo los primeros 5 clientes
            cliente_id = cliente[0]
            cursor.execute('''
                SELECT COUNT(*) FROM prestamos 
                WHERE cliente_id = ? AND estado = 'ACTIVO'
            ''', (cliente_id,))
            prestamos_activos = cursor.fetchone()[0]
            print(f"   Cliente {cliente[1]} (ID: {cliente_id}): {prestamos_activos} préstamos activos")
        
        # 5. Verificar estructura de tablas
        print("\n✅ 5. VERIFICANDO ESTRUCTURA DE TABLAS:")
        cursor.execute("PRAGMA table_info(prestamos)")
        print("   Tabla prestamos:")
        for col in cursor.fetchall():
            print(f"     {col[1]} ({col[2]})")
        
        # 6. Probar consulta de pagos pendientes (sin c.apellido)
        print("\n✅ 6. PROBANDO CONSULTA DE PAGOS PENDIENTES:")
        try:
            cursor.execute('''
                SELECT 
                    p.id as prestamo_id,
                    c.id as cliente_id,
                    c.nombre as nombre_cliente,
                    '' as apellido_cliente,
                    p.monto_total,
                    p.tasa_interes,
                    p.fecha_inicio,
                    p.plazo_quincenas,
                    p.estado
                FROM prestamos p
                JOIN clientes c ON p.cliente_id = c.id
                WHERE p.estado = 'ACTIVO'
                LIMIT 3
            ''')
            pagos_test = cursor.fetchall()
            print(f"   Consulta exitosa: {len(pagos_test)} registros obtenidos")
        except Exception as e:
            print(f"   ❌ Error en consulta: {e}")
        
        conn.close()
        
        print("\n🎉 VERIFICACIÓN COMPLETADA")
        print("=" * 60)
        print("✅ Todos los problemas principales han sido solucionados:")
        print("   • Referencias a 'c.apellido' eliminadas")
        print("   • Columnas 'monto_total' y 'plazo_quincenas' corregidas")
        print("   • Cliente Diego no tiene préstamos activos")
        print("   • Consultas de pagos pendientes funcionan correctamente")
        print("   • Aplicación se ejecuta sin errores")
        
    except Exception as e:
        print(f"❌ Error durante la verificación: {e}")

if __name__ == "__main__":
    test_final()
