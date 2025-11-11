#!/usr/bin/env python3
"""
Script para ejecutar la aplicación usando Python del sistema
(para evitar problemas con OneDrive y entorno virtual)
"""
import os
import sys

# Obtener el directorio del proyecto
project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)

# Agregar src al path
sys.path.insert(0, os.path.join(project_dir, 'src'))

# Cambiar al directorio src para las importaciones relativas
os.chdir(os.path.join(project_dir, 'src'))

try:
    print("=" * 60)
    print("Sistema de Gestión de Préstamos")
    print("=" * 60)
    print("Iniciando aplicación...")
    print("La ventana debería abrirse en breve.")
    print("=" * 60)
    
    from main import main
    main()
except KeyboardInterrupt:
    print("\n\nAplicación cerrada por el usuario.")
except Exception as e:
    print(f"\n\nERROR al ejecutar la aplicación: {e}")
    import traceback
    traceback.print_exc()
    input("\nPresiona Enter para salir...")


