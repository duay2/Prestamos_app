#!/usr/bin/env python3
"""
Script para agregar restricción UNIQUE a la tabla clientes y limpiar duplicados
"""

import sqlite3
import os

def get_db_path():
    """Obtener la ruta absoluta de la base de datos"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'prestamos.db')
    return db_path

def limpiar_duplicados():
    """Eliminar clientes duplicados, manteniendo el más antiguo"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"Error: No se encuentra la base de datos en {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Buscando clientes duplicados...")
        
        # Encontrar duplicados por nombre (case-insensitive)
        cursor.execute('''
            SELECT UPPER(TRIM(nombre)) as nombre_upper, COUNT(*) as count
            FROM clientes
            GROUP BY nombre_upper
            HAVING count > 1
        ''')
        
        duplicados = cursor.fetchall()
        
        if not duplicados:
            print("No se encontraron clientes duplicados.")
            return
        
        print(f"Se encontraron {len(duplicados)} grupos de clientes duplicados.")
        
        total_eliminados = 0
        
        for nombre_upper, count in duplicados:
            # Obtener todos los clientes con este nombre
            cursor.execute('''
                SELECT id, nombre, fecha_registro
                FROM clientes
                WHERE UPPER(TRIM(nombre)) = ?
                ORDER BY fecha_registro ASC, id ASC
            ''', (nombre_upper,))
            
            clientes = cursor.fetchall()
            
            # Mantener el primero (más antiguo) y eliminar los demás
            if len(clientes) > 1:
                cliente_original = clientes[0]
                duplicados_lista = clientes[1:]
                
                print(f"\n  Cliente: {cliente_original[1]}")
                print(f"    Manteniendo ID {cliente_original[0]} (registrado: {cliente_original[2]})")
                
                for dup_id, dup_nombre, dup_fecha in duplicados_lista:
                    # Verificar si tiene préstamos asociados
                    cursor.execute('SELECT COUNT(*) FROM prestamos WHERE cliente_id = ?', (dup_id,))
                    tiene_prestamos = cursor.fetchone()[0] > 0
                    
                    if tiene_prestamos:
                        print(f"    NO se puede eliminar ID {dup_id}: tiene préstamos asociados")
                    else:
                        cursor.execute('DELETE FROM clientes WHERE id = ?', (dup_id,))
                        total_eliminados += 1
                        print(f"    Eliminado ID {dup_id} (registrado: {dup_fecha})")
        
        conn.commit()
        print(f"\nTotal de duplicados eliminados: {total_eliminados}")
        print("Limpieza completada.")
        
    except sqlite3.Error as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

def agregar_restriccion_unique():
    """Agregar restricción UNIQUE al campo nombre (requiere recrear la tabla)"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"Error: No se encuentra la base de datos en {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Verificando restricciones existentes...")
        
        # Verificar si ya existe un índice único
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_clientes_nombre_unique'
        ''')
        
        if cursor.fetchone():
            print("La restricción UNIQUE ya existe.")
            return
        
        print("Creando índice único en el campo nombre...")
        
        # Crear índice único (SQLite no soporta UNIQUE directamente en ALTER TABLE)
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_clientes_nombre_unique 
            ON clientes(UPPER(TRIM(nombre)))
        ''')
        
        conn.commit()
        print("Restricción UNIQUE agregada exitosamente.")
        
    except sqlite3.OperationalError as e:
        if "UNIQUE constraint failed" in str(e):
            print("Error: Existen duplicados en la base de datos.")
            print("Ejecuta primero limpiar_duplicados() antes de agregar la restricción.")
        else:
            print(f"Error: {e}")
        conn.rollback()
    except sqlite3.Error as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """Función principal"""
    print("=" * 60)
    print("Script de Limpieza de Duplicados y Restricciones")
    print("=" * 60)
    
    # Primero limpiar duplicados
    print("\n1. Limpiando duplicados...")
    limpiar_duplicados()
    
    # Luego agregar restricción
    print("\n2. Agregando restricción UNIQUE...")
    agregar_restriccion_unique()
    
    print("\n" + "=" * 60)
    print("Proceso completado.")
    print("=" * 60)

if __name__ == "__main__":
    main()




