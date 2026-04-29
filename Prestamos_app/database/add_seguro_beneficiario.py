#!/usr/bin/env python3
"""
Script de migración para agregar campos de seguro y beneficiario a la tabla prestamos
"""

import sqlite3
import os

def get_db_path():
    """Obtener la ruta absoluta de la base de datos"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'prestamos.db')
    return db_path

def agregar_campos_seguro_beneficiario():
    """Agregar campos tiene_seguro y beneficiario a la tabla prestamos"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"Error: No se encuentra la base de datos en {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Verificando estructura de la tabla prestamos...")
        
        # Verificar si los campos ya existen
        cursor.execute("PRAGMA table_info(prestamos)")
        columnas = cursor.fetchall()
        nombres_columnas = [col[1] for col in columnas]
        
        if 'tiene_seguro' in nombres_columnas and 'beneficiario' in nombres_columnas:
            print("Los campos tiene_seguro y beneficiario ya existen.")
            return True
        
        print("Agregando campos tiene_seguro y beneficiario...")
        
        # Agregar campo tiene_seguro (INTEGER, 0 o 1)
        if 'tiene_seguro' not in nombres_columnas:
            cursor.execute('''
                ALTER TABLE prestamos 
                ADD COLUMN tiene_seguro INTEGER DEFAULT 0 CHECK (tiene_seguro IN (0, 1))
            ''')
            print("  [OK] Campo 'tiene_seguro' agregado")
        
        # Agregar campo beneficiario (TEXT, nullable)
        if 'beneficiario' not in nombres_columnas:
            cursor.execute('''
                ALTER TABLE prestamos 
                ADD COLUMN beneficiario TEXT
            ''')
            print("  [OK] Campo 'beneficiario' agregado")
        
        conn.commit()
        print("\n[OK] Migracion completada exitosamente.")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error durante la migración: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Función principal"""
    print("=" * 60)
    print("Script de Migración: Agregar Seguro y Beneficiario")
    print("=" * 60)
    
    if agregar_campos_seguro_beneficiario():
        print("\n" + "=" * 60)
        print("La base de datos está lista para usar con los nuevos campos.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Error durante la migración. Revisa los mensajes anteriores.")
        print("=" * 60)

if __name__ == "__main__":
    main()

