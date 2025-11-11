"""
Módulo para la gestión de configuración de la aplicación
"""

import json
import os
from typing import Optional

def get_config_path():
    """Obtener la ruta del archivo de configuración"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, 'config.json')
    return config_path

def cargar_configuracion() -> dict:
    """Cargar configuración desde archivo JSON"""
    config_path = get_config_path()
    config_default = {
        'prestamista_nombre': '',
        'prestamista_telefono': '',
        'prestamista_direccion': ''
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Asegurar que todas las claves existan
                for key in config_default:
                    if key not in config:
                        config[key] = config_default[key]
                return config
        except Exception:
            return config_default
    else:
        # Crear archivo con valores por defecto
        guardar_configuracion(config_default)
        return config_default

def guardar_configuracion(config: dict):
    """Guardar configuración en archivo JSON"""
    config_path = get_config_path()
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        raise Exception(f"Error al guardar configuración: {e}")

def obtener_prestamista_nombre() -> str:
    """Obtener el nombre del prestamista"""
    config = cargar_configuracion()
    return config.get('prestamista_nombre', '')

def guardar_prestamista_nombre(nombre: str):
    """Guardar el nombre del prestamista"""
    config = cargar_configuracion()
    config['prestamista_nombre'] = nombre
    guardar_configuracion(config)


