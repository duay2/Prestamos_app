#!/usr/bin/env python3
"""
Punto de entrada principal de la aplicación Sistema de Gestión de Préstamos
Implementa la ventana principal con notebook de pestañas
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import sys
import os
from datetime import datetime

# Importar módulos de la aplicación
from clientes import ClientesWindow
from prestamos import PrestamosWindow  # Módulo de préstamos listo
from pagos import PagosWindow          # Módulo de pagos listo
from reportes import ReportesWindow    # Módulo de reportes listo

class PrestamosApp:
    """Aplicación principal del Sistema de Gestión de Préstamos"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Gestión de Préstamos")
        self.root.geometry("1200x700")
        self.root.minsize(1000, 600)
        
        # Configurar icono (opcional)
        try:
            self.root.iconbitmap('assets/icon.ico')
        except:
            pass  # Si no existe el icono, continuar sin él
        
        # Variables de la aplicación
        self.db_connection = None
        self.notebook = None
        self.clientes_window = None
        self.prestamos_window = None
        self.pagos_window = None
        self.reportes_window = None
        
        # Configurar la aplicación
        self.setup_database()
        self.create_menu()
        self.create_widgets()
        self.setup_bindings()
        
        # Mostrar información de inicio
        self.show_welcome_message()
    
    def setup_database(self):
        """Configurar y verificar la base de datos"""
        try:
            # Asegurar que el directorio database existe
            os.makedirs('../database', exist_ok=True)
            
            # Conectar a la base de datos
            self.db_connection = sqlite3.connect('../database/prestamos.db')
            
            # Verificar si las tablas existen
            self.verify_database_tables()
            
            print("✅ Base de datos conectada correctamente")
            
        except Exception as e:
            messagebox.showerror(
                "Error de Base de Datos",
                f"No se pudo conectar a la base de datos:\n{str(e)}\n\n"
                "Asegúrate de ejecutar primero: python database/init_db.py"
            )
            sys.exit(1)
    
    def verify_database_tables(self):
        """Verificar que las tablas necesarias existan"""
        cursor = self.db_connection.cursor()
        
        # Lista de tablas requeridas
        required_tables = ['clientes', 'prestamos', 'pagos']
        
        # Verificar cada tabla
        for table in required_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                raise Exception(f"La tabla '{table}' no existe en la base de datos")
        
        print("✅ Todas las tablas verificadas correctamente")
    
    def create_menu(self):
        """Crear menú principal de la aplicación"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menú Archivo
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Nuevo Cliente", command=self.nuevo_cliente)
        file_menu.add_command(label="Nuevo Préstamo", command=self.nuevo_prestamo)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.quit_app)
        
        # Menú Gestión
        gestion_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Gestión", menu=gestion_menu)
        gestion_menu.add_command(label="Clientes", command=lambda: self.notebook.select(0))
        gestion_menu.add_command(label="Préstamos", command=lambda: self.notebook.select(1))
        gestion_menu.add_command(label="Pagos", command=lambda: self.notebook.select(2))
        gestion_menu.add_command(label="Reportes", command=lambda: self.notebook.select(3))
        
        # Menú Reportes
        reportes_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Reportes", menu=reportes_menu)
        reportes_menu.add_command(label="Resumen General", command=self.mostrar_resumen)
        reportes_menu.add_command(label="Préstamos Activos", command=self.mostrar_prestamos_activos)
        reportes_menu.add_command(label="Pagos del Mes", command=self.mostrar_pagos_mes)
        
        # Menú Herramientas
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Herramientas", menu=tools_menu)
        tools_menu.add_command(label="Respaldar Base de Datos", command=self.respaldar_db)
        tools_menu.add_command(label="Restaurar Base de Datos", command=self.restaurar_db)
        tools_menu.add_separator()
        tools_menu.add_command(label="Configuración", command=self.mostrar_configuracion)
        
        # Menú Ayuda
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        help_menu.add_command(label="Manual de Usuario", command=self.mostrar_manual)
        help_menu.add_command(label="Acerca de", command=self.mostrar_acerca_de)
    
    def create_widgets(self):
        """Crear widgets principales de la aplicación"""
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Barra de estado
        self.status_bar = ttk.Label(
            main_frame, 
            text="Sistema de Gestión de Préstamos - Listo",
            relief='sunken',
            anchor='w'
        )
        self.status_bar.pack(side='bottom', fill='x', pady=(5, 0))
        
        # Notebook principal
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True, pady=(0, 5))
        
        # Crear pestañas
        self.create_clientes_tab()
        self.create_prestamos_tab()
        self.create_pagos_tab()
        self.create_reportes_tab()
        
        # Configurar eventos del notebook
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)
    
    def create_clientes_tab(self):
        """Crear pestaña de clientes"""
        try:
            self.clientes_window = ClientesWindow(self.notebook)
            self.notebook.add(self.clientes_window, text="👥 Clientes")
            print("✅ Pestaña de Clientes creada")
        except Exception as e:
            print(f"❌ Error al crear pestaña de Clientes: {e}")
            # Crear pestaña de error
            error_frame = ttk.Frame(self.notebook)
            ttk.Label(error_frame, text=f"Error al cargar módulo de Clientes:\n{str(e)}", 
                     foreground='red').pack(pady=50)
            self.notebook.add(error_frame, text="👥 Clientes")
    
    def create_prestamos_tab(self):
        """Crear pestaña de préstamos"""
        try:
            self.prestamos_window = PrestamosWindow(self.notebook)
            self.notebook.add(self.prestamos_window, text="💰 Préstamos")
            print("✅ Pestaña de Préstamos creada")
        except Exception as e:
            print(f"❌ Error al crear pestaña de Préstamos: {e}")
            # Crear pestaña de error
            error_frame = ttk.Frame(self.notebook)
            ttk.Label(error_frame, text=f"Error al cargar módulo de Préstamos:\n{str(e)}", 
                     foreground='red').pack(pady=50)
            self.notebook.add(error_frame, text="💰 Préstamos")
    
    def create_pagos_tab(self):
        """Crear pestaña de pagos"""
        try:
            self.pagos_window = PagosWindow(self.notebook)
            self.notebook.add(self.pagos_window, text="💳 Pagos")
            print("✅ Pestaña de Pagos creada")
        except Exception as e:
            print(f"❌ Error al crear pestaña de Pagos: {e}")
            # Crear pestaña de error
            error_frame = ttk.Frame(self.notebook)
            ttk.Label(error_frame, text=f"Error al cargar módulo de Pagos:\n{str(e)}", 
                     foreground='red').pack(pady=50)
            self.notebook.add(error_frame, text="💳 Pagos")
    
    def create_reportes_tab(self):
        """Crear pestaña de reportes"""
        try:
            self.reportes_window = ReportesWindow(self.notebook)
            self.notebook.add(self.reportes_window, text="📊 Reportes")
            print("✅ Pestaña de Reportes creada")
        except Exception as e:
            print(f"❌ Error al crear pestaña de Reportes: {e}")
            # Crear pestaña de error
            error_frame = ttk.Frame(self.notebook)
            ttk.Label(error_frame, text=f"Error al cargar módulo de Reportes:\n{str(e)}", 
                     foreground='red').pack(pady=50)
            self.notebook.add(error_frame, text="📊 Reportes")
    
    def setup_bindings(self):
        """Configurar eventos de la aplicación"""
        # Evento de cierre de ventana
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        
        # Atajos de teclado
        self.root.bind('<Control-n>', lambda e: self.nuevo_cliente())
        self.root.bind('<Control-p>', lambda e: self.nuevo_prestamo())
        self.root.bind('<Control-q>', lambda e: self.quit_app())
        self.root.bind('<F1>', lambda e: self.mostrar_manual())
        self.root.bind('<F5>', lambda e: self.refresh_current_tab())
    
    def on_tab_changed(self, event):
        """Manejar cambio de pestaña"""
        current_tab = self.notebook.select()
        tab_id = self.notebook.index(current_tab)
        
        tab_names = ["Clientes", "Préstamos", "Pagos", "Reportes"]
        if 0 <= tab_id < len(tab_names):
            self.status_bar.config(text=f"Pestaña activa: {tab_names[tab_id]}")
    
    def show_welcome_message(self):
        """Mostrar mensaje de bienvenida"""
        try:
            # Obtener estadísticas básicas
            cursor = self.db_connection.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM clientes")
            num_clientes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM prestamos WHERE estado = 'ACTIVO'")
            num_prestamos_activos = cursor.fetchone()[0]
            
            welcome_text = f"Bienvenido al Sistema de Gestión de Préstamos\n\n" \
                          f"📊 Estado actual:\n" \
                          f"   👥 Clientes registrados: {num_clientes}\n" \
                          f"   💰 Préstamos activos: {num_prestamos_activos}\n\n" \
                          f"💡 Consejo: Usa Ctrl+N para nuevo cliente, Ctrl+P para nuevo préstamo"
            
            self.status_bar.config(text=welcome_text)
            
        except Exception as e:
            print(f"Error al mostrar estadísticas: {e}")
    
    # Métodos del menú
    def nuevo_cliente(self):
        """Abrir diálogo de nuevo cliente"""
        if self.clientes_window:
            self.notebook.select(0)  # Cambiar a pestaña de clientes
            self.clientes_window.agregar_cliente()
    
    def nuevo_prestamo(self):
        """Abrir diálogo de nuevo préstamo"""
        if self.prestamos_window:
            self.notebook.select(1)  # Cambiar a pestaña de préstamos
            self.prestamos_window.nuevo_prestamo()
        else:
            messagebox.showwarning("Advertencia", "Módulo de préstamos no disponible")
    
    def mostrar_resumen(self):
        """Mostrar resumen general"""
        try:
            cursor = self.db_connection.cursor()
            
            # Estadísticas generales
            cursor.execute("SELECT COUNT(*) FROM clientes")
            total_clientes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM prestamos")
            total_prestamos = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM prestamos WHERE estado = 'ACTIVO'")
            prestamos_activos = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(monto_total) FROM prestamos WHERE estado = 'ACTIVO'")
            total_prestado = cursor.fetchone()[0] or 0
            
            resumen = f"📊 RESUMEN GENERAL\n\n" \
                     f"👥 Total de Clientes: {total_clientes}\n" \
                     f"💰 Total de Préstamos: {total_prestamos}\n" \
                     f"✅ Préstamos Activos: {prestamos_activos}\n" \
                     f"💵 Monto Total Prestado: ${total_prestado:,.2f}"
            
            messagebox.showinfo("Resumen General", resumen)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar resumen: {e}")
    
    def mostrar_prestamos_activos(self):
        """Mostrar préstamos activos"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                SELECT p.id, c.nombre, p.monto_total, p.fecha_inicio, p.plazo_quincenas
                FROM prestamos p
                JOIN clientes c ON p.cliente_id = c.id
                WHERE p.estado = 'ACTIVO'
                ORDER BY p.fecha_inicio
            ''')
            
            prestamos = cursor.fetchall()
            
            if not prestamos:
                messagebox.showinfo("Préstamos Activos", "No hay préstamos activos")
                return
            
            # Crear ventana de reporte
            report_window = tk.Toplevel(self.root)
            report_window.title("Préstamos Activos")
            report_window.geometry("600x400")
            
            # Crear Treeview
            columns = ('ID', 'Cliente', 'Monto', 'Fecha Inicio', 'Plazo')
            tree = ttk.Treeview(report_window, columns=columns, show='headings')
            
            tree.heading('ID', text='ID')
            tree.heading('Cliente', text='Cliente')
            tree.heading('Monto', text='Monto')
            tree.heading('Fecha Inicio', text='Fecha Inicio')
            tree.heading('Plazo', text='Plazo (quincenas)')
            
            tree.column('ID', width=50)
            tree.column('Cliente', width=200)
            tree.column('Monto', width=100)
            tree.column('Fecha Inicio', width=100)
            tree.column('Plazo', width=100)
            
            for prestamo in prestamos:
                tree.insert('', 'end', values=prestamo)
            
            tree.pack(fill='both', expand=True, padx=10, pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al mostrar préstamos activos: {e}")
    
    def mostrar_pagos_mes(self):
        """Mostrar pagos del mes actual"""
        try:
            cursor = self.db_connection.cursor()
            current_month = datetime.now().strftime('%Y-%m')
            
            cursor.execute('''
                SELECT p.id, c.nombre, pag.fecha_pago, 
                       pag.monto_capital + pag.monto_interes + pag.monto_seguro as total
                FROM pagos pag
                JOIN prestamos p ON pag.prestamo_id = p.id
                JOIN clientes c ON p.cliente_id = c.id
                WHERE pag.fecha_pago LIKE ?
                ORDER BY pag.fecha_pago DESC
            ''', (f'{current_month}%',))
            
            pagos = cursor.fetchall()
            
            if not pagos:
                messagebox.showinfo("Pagos del Mes", f"No hay pagos registrados en {current_month}")
                return
            
            # Crear ventana de reporte
            report_window = tk.Toplevel(self.root)
            report_window.title(f"Pagos del Mes - {current_month}")
            report_window.geometry("500x400")
            
            # Crear Treeview
            columns = ('Préstamo', 'Cliente', 'Fecha', 'Total')
            tree = ttk.Treeview(report_window, columns=columns, show='headings')
            
            tree.heading('Préstamo', text='Préstamo ID')
            tree.heading('Cliente', text='Cliente')
            tree.heading('Fecha', text='Fecha Pago')
            tree.heading('Total', text='Total')
            
            tree.column('Préstamo', width=80)
            tree.column('Cliente', width=200)
            tree.column('Fecha', width=100)
            tree.column('Total', width=100)
            
            for pago in pagos:
                tree.insert('', 'end', values=pago)
            
            tree.pack(fill='both', expand=True, padx=10, pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al mostrar pagos del mes: {e}")
    
    def respaldar_db(self):
        """Respaldar base de datos"""
        messagebox.showinfo("Respaldar", "Función de respaldo en desarrollo")
    
    def restaurar_db(self):
        """Restaurar base de datos"""
        messagebox.showinfo("Restaurar", "Función de restauración en desarrollo")
    
    def mostrar_configuracion(self):
        """Mostrar ventana de configuración"""
        messagebox.showinfo("Configuración", "Ventana de configuración en desarrollo")
    
    def mostrar_manual(self):
        """Mostrar manual de usuario"""
        manual_text = """
📖 MANUAL DE USUARIO - Sistema de Gestión de Préstamos

🎯 FUNCIONES PRINCIPALES:

👥 GESTIÓN DE CLIENTES:
• Agregar nuevos clientes
• Editar información existente
• Eliminar clientes (sin préstamos activos)
• Buscar clientes por nombre o teléfono

💰 GESTIÓN DE PRÉSTAMOS:
• Crear nuevos préstamos
• Ver préstamos activos
• Calcular cuotas
• Generar tablas de amortización

💳 GESTIÓN DE PAGOS:
• Registrar pagos
• Ver historial de pagos
• Generar recibos
• Reportes de cobranza

⌨️ ATAJOS DE TECLADO:
• Ctrl+N: Nuevo cliente
• Ctrl+P: Nuevo préstamo
• Ctrl+Q: Salir
• F1: Manual de usuario
• F5: Actualizar vista actual

📊 REPORTES DISPONIBLES:
• Resumen general
• Préstamos activos
• Pagos del mes
        """
        messagebox.showinfo("Manual de Usuario", manual_text)
    
    def mostrar_acerca_de(self):
        """Mostrar información de la aplicación"""
        about_text = """
🏦 Sistema de Gestión de Préstamos
Versión 1.0.0

Desarrollado con Python y Tkinter

Características:
• Gestión completa de clientes
• Administración de préstamos
• Control de pagos
• Reportes y estadísticas
• Interfaz intuitiva

Tecnologías utilizadas:
• Python 3.x
• Tkinter (GUI)
• SQLite (Base de datos)
• FPDF (Generación de PDFs)

© 2024 - Todos los derechos reservados
        """
        messagebox.showinfo("Acerca de", about_text)
    
    def refresh_current_tab(self):
        """Actualizar la pestaña actual"""
        current_tab = self.notebook.select()
        tab_id = self.notebook.index(current_tab)
        
        if tab_id == 0 and self.clientes_window:  # Pestaña de clientes
            self.clientes_window.listar_clientes()
            self.status_bar.config(text="Vista de clientes actualizada")
    
    def quit_app(self):
        """Cerrar la aplicación de forma segura"""
        try:
            # Confirmar cierre
            if messagebox.askokcancel("Salir", "¿Estás seguro de que quieres salir?"):
                # Cerrar conexión de base de datos
                if self.db_connection:
                    self.db_connection.close()
                    print("✅ Conexión de base de datos cerrada")
                
                # Destruir ventana principal
                self.root.destroy()
                print("✅ Aplicación cerrada correctamente")
                
        except Exception as e:
            print(f"❌ Error al cerrar aplicación: {e}")
            self.root.destroy()

def main():
    """Función principal de la aplicación"""
    try:
        # Crear ventana principal
        root = tk.Tk()
        
        # Configurar tema (opcional)
        try:
            style = ttk.Style()
            style.theme_use('clam')  # Otros temas: 'alt', 'default', 'classic'
        except:
            pass
        
        # Crear aplicación
        app = PrestamosApp(root)
        
        # Centrar ventana
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        
        print("🚀 Aplicación iniciada correctamente")
        print("💡 Usa Ctrl+N para nuevo cliente, Ctrl+P para nuevo préstamo")
        
        # Iniciar loop principal
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Error al iniciar la aplicación: {e}")
        messagebox.showerror("Error Fatal", f"Error al iniciar la aplicación:\n{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
