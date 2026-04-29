#!/usr/bin/env python3
"""
Módulo para la gestión de tarifas de préstamos basado en matriz de tarifas fijas
Sistema PRESTAMAX - Matriz de pagos quincenales
"""

from typing import Dict, Optional
import math

# Matriz de tarifas fijas
# Estructura: {monto: {quincenas: cuota_quincenal}}
TARIFAS_MATRIZ = {
    1000: {6: 200, 8: 175, 10: 145, 12: 130, 14: 110, 16: 100},
    2000: {6: 400, 8: 350, 10: 290, 12: 260, 14: 220, 16: 200},
    3000: {6: 600, 8: 525, 10: 435, 12: 390, 14: 330, 16: 300},
    4000: {6: 800, 8: 700, 10: 580, 12: 520, 14: 440, 16: 400},
    5000: {6: 1000, 8: 895, 10: 740, 12: 650, 14: 575, 16: 525},
    6000: {6: 1200, 8: 1074, 10: 888, 12: 780, 14: 690, 16: 630},
    7000: {6: 1400, 8: 1253, 10: 1036, 12: 910, 14: 805, 16: 735},
    8000: {6: 1600, 8: 1432, 10: 1184, 12: 1040, 14: 920, 16: 840},
    9000: {6: 1800, 8: 1611, 10: 1332, 12: 1170, 14: 1035, 16: 945},
    10000: {6: 2000, 8: 1800, 10: 1500, 12: 1305, 14: 1150, 16: 1050},
}

# Quincenas disponibles
QUINCENAS_DISPONIBLES = [6, 8, 10, 12, 14, 16]

def obtener_cuota_quincenal(monto: float, quincenas: int) -> float:
    """
    Obtener la cuota quincenal basada en la matriz de tarifas
    
    Args:
        monto: Monto del préstamo
        quincenas: Número de quincenas (6, 8, 10, 12, 14, 16)
    
    Returns:
        float: Cuota quincenal a pagar
    
    Raises:
        ValueError: Si las quincenas no están disponibles o el monto es inválido
    """
    if quincenas not in QUINCENAS_DISPONIBLES:
        raise ValueError(f"Las quincenas deben ser una de: {QUINCENAS_DISPONIBLES}")
    
    if monto < 1000:
        raise ValueError("El monto mínimo es $1,000")
    
    # Redondear el monto a múltiplos de 1000 para facilitar el cálculo
    monto_base = math.floor(monto / 1000) * 1000
    
    # Si el monto está exactamente en la matriz
    if monto_base in TARIFAS_MATRIZ and quincenas in TARIFAS_MATRIZ[monto_base]:
        return float(TARIFAS_MATRIZ[monto_base][quincenas])
    
    # Si el monto es mayor a $10,000, calcular proporcionalmente
    if monto_base > 10000:
        # Usar la tarifa de $10,000 como base y multiplicar proporcionalmente
        tarifa_base = TARIFAS_MATRIZ[10000][quincenas]
        factor = monto_base / 10000
        return round(tarifa_base * factor, 2)
    
    # Interpolación para montos entre valores de la matriz
    # Encontrar el monto base inferior y superior
    montos_disponibles = sorted(TARIFAS_MATRIZ.keys())
    
    # Si el monto es menor que el mínimo, usar el mínimo
    if monto_base < montos_disponibles[0]:
        return float(TARIFAS_MATRIZ[montos_disponibles[0]][quincenas])
    
    # Si el monto está entre dos valores, interpolar
    monto_inferior = None
    monto_superior = None
    
    for i, monto_ref in enumerate(montos_disponibles):
        if monto_base <= monto_ref:
            monto_superior = monto_ref
            if i > 0:
                monto_inferior = montos_disponibles[i - 1]
            else:
                monto_inferior = monto_ref
            break
    
    # Si no se encontró, usar el máximo disponible
    if monto_superior is None:
        monto_inferior = montos_disponibles[-1]
        monto_superior = montos_disponibles[-1]
    
    # Calcular cuotas
    cuota_inferior = TARIFAS_MATRIZ[monto_inferior][quincenas]
    cuota_superior = TARIFAS_MATRIZ[monto_superior][quincenas]
    
    # Si son iguales, retornar directamente
    if monto_inferior == monto_superior:
        return float(cuota_inferior)
    
    # Interpolación lineal
    factor = (monto_base - monto_inferior) / (monto_superior - monto_inferior)
    cuota_interpolada = cuota_inferior + (cuota_superior - cuota_inferior) * factor
    
    return round(cuota_interpolada, 2)

def calcular_total_pagar(monto: float, quincenas: int) -> float:
    """
    Calcular el total a pagar (cuota quincenal * número de quincenas)
    
    Args:
        monto: Monto del préstamo
        quincenas: Número de quincenas
    
    Returns:
        float: Total a pagar
    """
    cuota_quincenal = obtener_cuota_quincenal(monto, quincenas)
    return round(cuota_quincenal * quincenas, 2)

def calcular_interes_total(monto: float, quincenas: int) -> float:
    """
    Calcular el interés total (diferencia entre total a pagar y monto del préstamo)
    
    Args:
        monto: Monto del préstamo
        quincenas: Número de quincenas
    
    Returns:
        float: Interés total
    """
    total_pagar = calcular_total_pagar(monto, quincenas)
    return round(total_pagar - monto, 2)

def obtener_todos_montos_disponibles() -> list:
    """Obtener lista de todos los montos disponibles en la matriz"""
    return sorted(TARIFAS_MATRIZ.keys())

def obtener_todas_quincenas() -> list:
    """Obtener lista de todas las quincenas disponibles"""
    return QUINCENAS_DISPONIBLES.copy()

def validar_monto_y_quincenas(monto: float, quincenas: int) -> tuple[bool, Optional[str]]:
    """
    Validar que el monto y las quincenas sean válidos
    
    Args:
        monto: Monto del préstamo
        quincenas: Número de quincenas
    
    Returns:
        tuple: (es_valido, mensaje_error)
    """
    if monto < 1000:
        return False, "El monto mínimo es $1,000"
    
    if quincenas not in QUINCENAS_DISPONIBLES:
        return False, f"Las quincenas deben ser una de: {QUINCENAS_DISPONIBLES}"
    
    return True, None

# Función para obtener la matriz completa (útil para mostrar en la interfaz)
def obtener_matriz_completa() -> Dict:
    """
    Obtener la matriz completa de tarifas
    
    Returns:
        Dict: Matriz completa con todas las combinaciones
    """
    return TARIFAS_MATRIZ.copy()




