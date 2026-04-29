#!/usr/bin/env python3
"""
Script para generar el logo del Sistema de Gestión de Préstamos
Crea un logo con escudo azul, flecha dorada y letra P
"""

from PIL import Image, ImageDraw, ImageFont
import os

def crear_logo():
    """Crear el logo del sistema"""
    # Dimensiones del logo (más grande para mejor visibilidad)
    width, height = 500, 250
    
    # Crear imagen con fondo blanco para mejor contraste
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Colores basados en la imagen
    azul_oscuro = (30, 58, 95)  # #1E3A5F
    azul_claro = (74, 144, 226)  # #4A90E2
    azul_medio = (91, 163, 245)  # #5BA3F5
    dorado_oscuro = (255, 215, 0)  # #FFD700
    dorado_claro = (255, 223, 0)  # #FFDF00
    blanco = (255, 255, 255)
    
    # 1. Dibujar escudo (lado izquierdo) - más grande
    shield_x = 60
    shield_y = 40
    shield_width = 150
    shield_height = 170
    
    # Contorno del escudo
    shield_points = [
        (shield_x, shield_y + shield_height * 0.2),  # Punto superior izquierdo
        (shield_x + shield_width * 0.3, shield_y),  # Parte superior izquierda
        (shield_x + shield_width * 0.7, shield_y),  # Parte superior derecha
        (shield_x + shield_width, shield_y + shield_height * 0.2),  # Punto superior derecho
        (shield_x + shield_width, shield_y + shield_height * 0.8),  # Parte inferior derecha
        (shield_x + shield_width * 0.5, shield_y + shield_height),  # Punta inferior
        (shield_x, shield_y + shield_height * 0.8),  # Parte inferior izquierda
    ]
    
    # Relleno del escudo con gradiente azul (simulado con líneas)
    for j in range(shield_height):
        y_pos = shield_y + j
        if shield_y <= y_pos <= shield_y + shield_height:
            # Interpolar color de azul oscuro a azul claro
            ratio = j / shield_height
            r = int(azul_oscuro[0] + (azul_claro[0] - azul_oscuro[0]) * ratio)
            g = int(azul_oscuro[1] + (azul_claro[1] - azul_oscuro[1]) * ratio)
            b = int(azul_oscuro[2] + (azul_claro[2] - azul_oscuro[2]) * ratio)
            color = (r, g, b)
            
            # Dibujar línea horizontal dentro del escudo
            x_start = shield_x + int(shield_width * 0.15)
            x_end = shield_x + int(shield_width * 0.85)
            draw.line([(x_start, y_pos), (x_end, y_pos)], fill=color, width=1)
    
    # Contorno del escudo en azul oscuro
    draw.polygon(shield_points, outline=azul_oscuro, width=4)
    
    # 2. Dibujar flecha/graph dorado dentro del escudo
    arrow_start_x = shield_x + 20
    arrow_start_y = shield_y + shield_height - 30
    arrow_mid_x = shield_x + shield_width // 2
    arrow_mid_y = shield_y + 40
    arrow_end_x = shield_x + shield_width - 20
    arrow_end_y = shield_y + 20
    
    # Línea base (gráfico)
    graph_points = [
        (arrow_start_x, arrow_start_y),
        (arrow_start_x + 15, arrow_start_y - 20),
        (arrow_start_x + 30, arrow_start_y - 15),
        (arrow_start_x + 45, arrow_start_y - 35),
        (arrow_mid_x, arrow_mid_y),
    ]
    
    # Dibujar gráfico con gradiente dorado
    for i in range(len(graph_points) - 1):
        x1, y1 = graph_points[i]
        x2, y2 = graph_points[i + 1]
        # Interpolar color dorado
        for j in range(20):
            ratio = j / 20
            r = int(dorado_oscuro[0] + (dorado_claro[0] - dorado_oscuro[0]) * ratio)
            g = int(dorado_oscuro[1] + (dorado_claro[1] - dorado_oscuro[1]) * ratio)
            b = int(dorado_oscuro[2] + (dorado_claro[2] - dorado_oscuro[2]) * ratio)
            color = (r, g, b)
            x = int(x1 + (x2 - x1) * ratio)
            y = int(y1 + (y2 - y1) * ratio)
            draw.ellipse([x-2, y-2, x+2, y+2], fill=color)
    
    # Dibujar flecha apuntando hacia arriba-derecha
    arrow_tip_x = arrow_end_x
    arrow_tip_y = arrow_end_y
    arrow_base_x = arrow_mid_x + 10
    arrow_base_y = arrow_mid_y - 10
    
    # Cuerpo de la flecha
    arrow_body = [
        (arrow_base_x, arrow_base_y),
        (arrow_tip_x - 15, arrow_tip_y + 5),
        (arrow_tip_x, arrow_tip_y),
    ]
    draw.polygon(arrow_body, fill=dorado_claro, outline=dorado_oscuro, width=2)
    
    # 3. Dibujar letra P dorada (lado derecho del escudo) - más grande
    p_x = shield_x + shield_width + 40
    p_y = shield_y + 10
    p_size = 130
    
    # Intentar usar una fuente más grande, si no está disponible usar una básica
    try:
        # Intentar usar fuente del sistema
        font = ImageFont.truetype("arial.ttf", p_size)
    except:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", p_size)
        except:
            # Fuente por defecto
            font = ImageFont.load_default()
    
    # Dibujar letra P dorada (con efecto de gradiente simulado)
    # Primero dibujar con color más oscuro ligeramente desplazado
    draw.text((p_x + 2, p_y + 2), "P", font=font, fill=dorado_oscuro)
    # Luego dibujar con color claro encima
    draw.text((p_x, p_y), "P", font=font, fill=dorado_claro)
    
    # 4. Agregar texto "GESTIÓN DE PRÉSTAMOS" debajo - más grande y en negrita
    try:
        text_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 28)
    except:
        try:
            text_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
        except:
            text_font = ImageFont.load_default()
    
    text = "GESTIÓN DE PRÉSTAMOS"
    text_bbox = draw.textbbox((0, 0), text, font=text_font)
    text_width = text_bbox[2] - text_bbox[0]
    text_x = (width - text_width) // 2
    text_y = height - 60
    
    # Dibujar texto con sombra para mejor legibilidad
    draw.text((text_x + 1, text_y + 1), text, font=text_font, fill=(200, 200, 200))
    draw.text((text_x, text_y), text, font=text_font, fill=azul_oscuro)
    
    return img

def main():
    """Función principal"""
    # Crear directorio assets si no existe
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, 'assets')
    os.makedirs(assets_dir, exist_ok=True)
    
    # Crear logo
    print("Generando logo...")
    logo = crear_logo()
    
    # Guardar logo en diferentes formatos
    logo_path_png = os.path.join(assets_dir, 'logo.png')
    logo_path_ico = os.path.join(assets_dir, 'logo.ico')
    
    # Guardar PNG
    logo.save(logo_path_png, 'PNG')
    print(f"Logo guardado en: {logo_path_png}")
    
    # Guardar ICO (para icono de ventana)
    logo_ico = logo.resize((64, 64), Image.Resampling.LANCZOS)
    logo_ico.save(logo_path_ico, 'ICO')
    print(f"Icono guardado en: {logo_path_ico}")
    
    print("¡Logo generado exitosamente!")

if __name__ == "__main__":
    main()

