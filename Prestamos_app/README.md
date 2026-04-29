# Sistema de Gestión de Préstamos

Una aplicación completa para la gestión de préstamos, clientes, pagos y generación de recibos desarrollada en Python con interfaz gráfica Tkinter.

## Características

- **Gestión de Clientes**: Crear, editar, eliminar y buscar clientes
- **Gestión de Préstamos**: Crear préstamos, calcular cuotas y tabla de amortización
- **Gestión de Pagos**: Registrar pagos y calcular saldos pendientes
- **Generación de Recibos**: Crear recibos en formato PDF
- **Base de Datos SQLite**: Almacenamiento local y confiable
- **Interfaz Gráfica**: Aplicación de escritorio fácil de usar

## Estructura del Proyecto

```
prestamos_app/
├── .vscode/                 # Configuración de VS Code
├── database/               # Base de datos SQLite
├── src/                    # Código fuente
│   ├── __init__.py         # Paquete Python
│   ├── main.py            # Aplicación principal
│   ├── clientes.py        # Gestión de clientes
│   ├── prestamos.py       # Gestión de préstamos
│   ├── pagos.py           # Gestión de pagos
│   └── recibos.py         # Generación de recibos
├── requirements.txt        # Dependencias
└── README.md              # Documentación
```

## Instalación

### Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Clonar o descargar el proyecto**
   ```bash
   git clone <url-del-repositorio>
   cd prestamos_app
   ```

2. **Crear entorno virtual (recomendado)**
   ```bash
   python -m venv venv
   
   # En Windows
   venv\Scripts\activate
   
   # En macOS/Linux
   source venv/bin/activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

## Uso

### Ejecutar la Aplicación

```bash
cd src
python main.py
```

### Funcionalidades Principales

#### 1. Gestión de Clientes
- **Crear Cliente**: Agregar nuevos clientes con información completa
- **Editar Cliente**: Modificar datos de clientes existentes
- **Eliminar Cliente**: Remover clientes (solo si no tienen préstamos activos)
- **Buscar Cliente**: Encontrar clientes por nombre o apellido

#### 2. Gestión de Préstamos
- **Crear Préstamo**: Establecer nuevos préstamos con:
  - Cliente seleccionado
  - Monto del préstamo
  - Tasa de interés anual
  - Plazo en meses
  - Fecha de inicio
- **Calcular Cuota**: Cálculo automático de cuota mensual
- **Tabla de Amortización**: Generar tabla completa de pagos
- **Estados del Préstamo**: ACTIVO, PAGADO, VENCIDO, CANCELADO

#### 3. Gestión de Pagos
- **Registrar Pago**: Anotar pagos realizados por los clientes
- **Tipos de Pago**: CUOTA, PAGO_PARCIAL, PAGO_TOTAL
- **Historial de Pagos**: Ver todos los pagos de un préstamo
- **Saldo Pendiente**: Cálculo automático del saldo restante

#### 4. Generación de Recibos
- **Recibo de Pago**: PDF individual por cada pago
- **Recibo Detallado**: PDF con historial completo del préstamo
- **Recibo Mensual**: Resumen de pagos por mes
- **Formato Profesional**: Recibos con diseño profesional

## Base de Datos

La aplicación utiliza SQLite como base de datos local. Las tablas principales son:

### Tabla `clientes`
- `id`: Identificador único
- `nombre`: Nombre del cliente
- `apellido`: Apellido del cliente
- `telefono`: Número de teléfono
- `email`: Dirección de correo electrónico
- `direccion`: Dirección física
- `fecha_registro`: Fecha de registro

### Tabla `prestamos`
- `id`: Identificador único
- `cliente_id`: Referencia al cliente
- `monto`: Monto del préstamo
- `tasa_interes`: Tasa de interés anual (%)
- `plazo_meses`: Duración en meses
- `fecha_inicio`: Fecha de inicio del préstamo
- `estado`: Estado actual del préstamo

### Tabla `pagos`
- `id`: Identificador único
- `prestamo_id`: Referencia al préstamo
- `monto`: Monto del pago
- `fecha_pago`: Fecha del pago
- `tipo_pago`: Tipo de pago realizado

## Cálculos Financieros

### Cuota Mensual
La aplicación utiliza la fórmula de cuota fija para calcular los pagos mensuales:

```
Cuota = P × (r × (1 + r)^n) / ((1 + r)^n - 1)
```

Donde:
- P = Principal (monto del préstamo)
- r = Tasa de interés mensual (tasa anual / 12 / 100)
- n = Número total de pagos (plazo en meses)

### Tabla de Amortización
Para cada mes se calcula:
- **Interés**: Saldo pendiente × tasa mensual
- **Capital**: Cuota - Interés
- **Saldo Pendiente**: Saldo anterior - Capital

## Módulos del Sistema

### `main.py`
Aplicación principal con interfaz gráfica Tkinter. Incluye:
- Ventana principal con pestañas
- Gestión de clientes (formulario y tabla)
- Estructura base para otras funcionalidades

### `clientes.py`
Gestión completa de clientes:
- `ClienteManager`: Clase principal para operaciones CRUD
- Funciones de conveniencia para uso directo
- Validaciones y estadísticas

### `prestamos.py`
Gestión de préstamos y cálculos financieros:
- `PrestamoManager`: Clase principal para préstamos
- Cálculo de cuotas y tabla de amortización
- Verificación de vencimientos
- Estadísticas de préstamos

### `pagos.py`
Gestión de pagos y saldos:
- `PagoManager`: Clase principal para pagos
- Registro y consulta de pagos
- Cálculo de saldos pendientes
- Historial de pagos

### `recibos.py`
Generación de recibos en PDF:
- `ReciboManager`: Clase principal para recibos
- Diferentes tipos de recibos
- Formato profesional con FPDF
- Organización automática de archivos

## Configuración

### Archivo de Configuración
La aplicación utiliza configuraciones por defecto, pero puedes modificar:
- Ruta de la base de datos
- Formato de fechas
- Configuración de PDFs

### Personalización
- Modificar estilos de la interfaz en `main.py`
- Ajustar formato de recibos en `recibos.py`
- Personalizar cálculos financieros en `prestamos.py`

## Mantenimiento

### Respaldo de Base de Datos
```bash
# Crear respaldo
sqlite3 database/prestamos.db ".backup backup/prestamos_backup.db"

# Restaurar respaldo
sqlite3 database/prestamos.db ".restore backup/prestamos_backup.db"
```

### Limpieza de Archivos
- Los recibos se guardan en la carpeta `recibos/`
- Se recomienda limpiar periódicamente archivos antiguos

## Solución de Problemas

### Errores Comunes

1. **Error de conexión a base de datos**
   - Verificar que la carpeta `database/` existe
   - Comprobar permisos de escritura

2. **Error al generar PDF**
   - Verificar que FPDF está instalado
   - Comprobar permisos de escritura en carpeta de recibos

3. **Error de importación**
   - Verificar que todas las dependencias están instaladas
   - Usar entorno virtual

### Logs y Debugging
La aplicación muestra mensajes de error en ventanas emergentes. Para debugging avanzado, revisar:
- Consola de Python
- Archivos de log del sistema

## Contribución

### Desarrollo
1. Fork del proyecto
2. Crear rama para nueva funcionalidad
3. Implementar cambios
4. Probar exhaustivamente
5. Crear Pull Request

### Mejoras Sugeridas
- Exportación a Excel
- Gráficos y reportes
- Backup automático
- Múltiples monedas
- Notificaciones por email

## Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo LICENSE para más detalles.

## Contacto

Para soporte técnico o consultas:
- Crear un issue en el repositorio
- Contactar al desarrollador principal

## Changelog

### Versión 1.0.0
- Gestión básica de clientes
- Gestión de préstamos con cálculos financieros
- Sistema de pagos
- Generación de recibos PDF
- Interfaz gráfica completa

---

**Nota**: Esta aplicación está diseñada para uso educativo y de pequeñas empresas. Para uso comercial a gran escala, se recomienda implementar medidas de seguridad adicionales.
