#!/usr/bin/env python3
"""
Script de inicialización de la base de datos SQLite
Crea las tablas necesarias para el sistema de gestión de préstamos
"""

import sqlite3
import os
from datetime import datetime

def create_database():
    """Crear la base de datos y las tablas"""
    
    # Asegurar que el directorio database existe
    os.makedirs('database', exist_ok=True)
    
    # Conectar a la base de datos (se crea si no existe)
    conn = sqlite3.connect('database/prestamos.db')
    cursor = conn.cursor()
    
    try:
        # Habilitar foreign keys
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # Tabla 1: clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                telefono TEXT,
                direccion TEXT,
                fecha_registro DATE DEFAULT CURRENT_DATE
            )
        ''')
        
        # Tabla 2: prestamos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prestamos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                monto_total REAL NOT NULL CHECK (monto_total > 0),
                tasa_interes REAL NOT NULL CHECK (tasa_interes >= 0),
                fecha_inicio DATE NOT NULL,
                plazo_quincenas INTEGER NOT NULL CHECK (plazo_quincenas > 0),
                estado TEXT NOT NULL DEFAULT 'ACTIVO' 
                    CHECK (estado IN ('ACTIVO', 'PAGADO', 'VENCIDO', 'CANCELADO')),
                detalles TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE RESTRICT
            )
        ''')
        
        # Tabla 3: pagos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pagos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prestamo_id INTEGER NOT NULL,
                numero_quincena INTEGER NOT NULL CHECK (numero_quincena > 0),
                fecha_pago DATE NOT NULL,
                monto_capital REAL NOT NULL CHECK (monto_capital >= 0),
                monto_interes REAL NOT NULL CHECK (monto_interes >= 0),
                monto_seguro REAL DEFAULT 0 CHECK (monto_seguro >= 0),
                recibido_por TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prestamo_id) REFERENCES prestamos (id) ON DELETE CASCADE
            )
        ''')
        
        # Crear índices para mejorar el rendimiento
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_prestamos_cliente ON prestamos(cliente_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_prestamos_estado ON prestamos(estado)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pagos_prestamo ON pagos(prestamo_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pagos_fecha ON pagos(fecha_pago)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes(nombre)')
        
        # Crear vista para información completa de préstamos
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS vista_prestamos_completa AS
            SELECT 
                p.id,
                p.cliente_id,
                c.nombre as nombre_cliente,
                c.telefono as telefono_cliente,
                p.monto_total,
                p.tasa_interes,
                p.fecha_inicio,
                p.plazo_quincenas,
                p.estado,
                p.detalles,
                p.fecha_creacion,
                COALESCE(SUM(pag.monto_capital + pag.monto_interes + pag.monto_seguro), 0) as total_pagado,
                p.monto_total - COALESCE(SUM(pag.monto_capital + pag.monto_interes + pag.monto_seguro), 0) as saldo_pendiente
            FROM prestamos p
            JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN pagos pag ON p.id = pag.prestamo_id
            GROUP BY p.id, p.cliente_id, c.nombre, c.telefono, p.monto_total, p.tasa_interes, 
                     p.fecha_inicio, p.plazo_quincenas, p.estado, p.detalles, p.fecha_creacion
        ''')
        
        # Crear vista para resumen de pagos por préstamo
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS vista_resumen_pagos AS
            SELECT 
                prestamo_id,
                COUNT(*) as total_pagos,
                SUM(monto_capital) as total_capital,
                SUM(monto_interes) as total_interes,
                SUM(monto_seguro) as total_seguro,
                SUM(monto_capital + monto_interes + monto_seguro) as total_general,
                MIN(fecha_pago) as primer_pago,
                MAX(fecha_pago) as ultimo_pago
            FROM pagos
            GROUP BY prestamo_id
        ''')
        
        # Confirmar cambios
        conn.commit()
        
        print("✅ Base de datos inicializada correctamente")
        print("📊 Tablas creadas:")
        print("   - clientes")
        print("   - prestamos") 
        print("   - pagos")
        print("📈 Índices creados para optimizar consultas")
        print("👁️  Vistas creadas:")
        print("   - vista_prestamos_completa")
        print("   - vista_resumen_pagos")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error al crear la base de datos: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

def insert_sample_data():
    """Insertar datos de ejemplo para pruebas"""
    
    conn = sqlite3.connect('database/prestamos.db')
    cursor = conn.cursor()
    
    try:
        # Insertar clientes de ejemplo
        clientes_ejemplo = [
            ('Juan Pérez', '555-0101', 'Calle Principal 123, Ciudad'),
            ('María García', '555-0102', 'Avenida Central 456, Ciudad'),
            ('Carlos López', '555-0103', 'Boulevard Norte 789, Ciudad'),
            ('Ana Martínez', '555-0104', 'Plaza Sur 321, Ciudad'),
            ('Roberto Silva', '555-0105', 'Calle Este 654, Ciudad')
        ]
        
        cursor.executemany('''
            INSERT INTO clientes (nombre, telefono, direccion)
            VALUES (?, ?, ?)
        ''', clientes_ejemplo)
        
        # Insertar préstamos de ejemplo
        prestamos_ejemplo = [
            (1, 50000.00, 2.5, '2024-01-15', 24, 'ACTIVO', 'Préstamo personal'),
            (2, 75000.00, 3.0, '2024-02-01', 36, 'ACTIVO', 'Préstamo para negocio'),
            (3, 30000.00, 2.0, '2024-01-20', 18, 'ACTIVO', 'Préstamo de emergencia'),
            (4, 100000.00, 2.8, '2024-02-10', 48, 'ACTIVO', 'Préstamo para vehículo'),
            (5, 25000.00, 2.2, '2024-02-15', 12, 'ACTIVO', 'Préstamo pequeño')
        ]
        
        cursor.executemany('''
            INSERT INTO prestamos (cliente_id, monto_total, tasa_interes, fecha_inicio, 
                                  plazo_quincenas, estado, detalles)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', prestamos_ejemplo)
        
        # Insertar pagos de ejemplo
        pagos_ejemplo = [
            (1, 1, '2024-01-30', 2000.00, 625.00, 50.00, 'Juan Pérez'),
            (1, 2, '2024-02-15', 2000.00, 600.00, 50.00, 'María García'),
            (2, 1, '2024-02-15', 2000.00, 1125.00, 75.00, 'Carlos López'),
            (3, 1, '2024-02-05', 1500.00, 300.00, 30.00, 'Ana Martínez'),
            (4, 1, '2024-02-25', 2000.00, 1400.00, 100.00, 'Roberto Silva')
        ]
        
        cursor.executemany('''
            INSERT INTO pagos (prestamo_id, numero_quincena, fecha_pago, monto_capital, 
                              monto_interes, monto_seguro, recibido_por)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', pagos_ejemplo)
        
        conn.commit()
        print("✅ Datos de ejemplo insertados correctamente")
        print("👥 5 clientes agregados")
        print("💰 5 préstamos agregados")
        print("💳 5 pagos agregados")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error al insertar datos de ejemplo: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

def show_database_info():
    """Mostrar información de la base de datos"""
    
    conn = sqlite3.connect('database/prestamos.db')
    cursor = conn.cursor()
    
    try:
        # Contar registros en cada tabla
        cursor.execute('SELECT COUNT(*) FROM clientes')
        num_clientes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM prestamos')
        num_prestamos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM pagos')
        num_pagos = cursor.fetchone()[0]
        
        # Mostrar estructura de tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = cursor.fetchall()
        
        print("\n📊 INFORMACIÓN DE LA BASE DE DATOS")
        print("=" * 50)
        print(f"📁 Ubicación: database/prestamos.db")
        print(f"📅 Creada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📋 Tablas: {len(tablas)}")
        
        for tabla in tablas:
            print(f"   - {tabla[0]}")
        
        print(f"\n📈 REGISTROS:")
        print(f"   👥 Clientes: {num_clientes}")
        print(f"   💰 Préstamos: {num_prestamos}")
        print(f"   💳 Pagos: {num_pagos}")
        
        # Mostrar algunos clientes
        cursor.execute('SELECT id, nombre, telefono FROM clientes LIMIT 3')
        clientes = cursor.fetchall()
        
        print(f"\n👥 CLIENTES (primeros 3):")
        for cliente in clientes:
            print(f"   ID {cliente[0]}: {cliente[1]} - {cliente[2]}")
        
        # Mostrar algunos préstamos
        cursor.execute('''
            SELECT p.id, c.nombre, p.monto_total, p.estado 
            FROM prestamos p 
            JOIN clientes c ON p.cliente_id = c.id 
            LIMIT 3
        ''')
        prestamos = cursor.fetchall()
        
        print(f"\n💰 PRÉSTAMOS (primeros 3):")
        for prestamo in prestamos:
            print(f"   ID {prestamo[0]}: {prestamo[1]} - ${prestamo[2]:,.2f} ({prestamo[3]})")
        
    except sqlite3.Error as e:
        print(f"❌ Error al obtener información: {e}")
        
    finally:
        conn.close()

def main():
    """Función principal"""
    print("🚀 INICIALIZANDO BASE DE DATOS DEL SISTEMA DE PRÉSTAMOS")
    print("=" * 60)
    
    # Crear base de datos
    if create_database():
        # Preguntar si insertar datos de ejemplo
        respuesta = input("\n¿Deseas insertar datos de ejemplo? (s/n): ").lower().strip()
        
        if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
            insert_sample_data()
        
        # Mostrar información
        show_database_info()
        
        print("\n✅ ¡Base de datos lista para usar!")
        print("💡 Puedes ejecutar la aplicación con: python src/main.py")
        
    else:
        print("\n❌ Error al inicializar la base de datos")

if __name__ == "__main__":
    main()
