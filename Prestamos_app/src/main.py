#!/usr/bin/env python3
"""
Punto de entrada principal de la aplicación Sistema de Gestión de Préstamos
Implementa la ventana principal con notebook de pestañas
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import sys
import os
import shutil
import time
from datetime import datetime
try:
    from PIL import Image, ImageTk, ImageGrab, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

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
        
        # Configurar color de fondo de la ventana principal
        self.root.configure(bg='#F5F7FA')
        
        # Configurar icono del logo
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_dir, 'assets', 'logo.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"[INFO] No se pudo cargar el icono: {e}")
        
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
            # Obtener el directorio base del proyecto (un nivel arriba de src)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_dir = os.path.join(base_dir, 'database')
            db_path = os.path.join(db_dir, 'prestamos.db')
            
            # Asegurar que el directorio database existe
            os.makedirs(db_dir, exist_ok=True)
            
            # Conectar a la base de datos usando ruta absoluta
            self.db_connection = sqlite3.connect(db_path)
            
            # Verificar si las tablas existen
            self.verify_database_tables()
            
            print("[OK] Base de datos conectada correctamente")
            
        except Exception as e:
            print(f"[ERROR] Error de base de datos: {e}")
            messagebox.showerror(
                "Error de Base de Datos",
                f"No se pudo conectar a la base de datos:\n{str(e)}\n\n"
                "Asegúrate de ejecutar primero: python database/init_db.py"
            )
            # No cerrar la aplicación, continuar con error
            self.db_connection = None
    
    def verify_database_tables(self):
        """Verificar que las tablas necesarias existan"""
        if not self.db_connection:
            raise Exception("No hay conexión a la base de datos")
            
        cursor = self.db_connection.cursor()
        
        # Lista de tablas requeridas
        required_tables = ['clientes', 'prestamos', 'pagos']
        
        # Verificar cada tabla
        for table in required_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                raise Exception(f"La tabla '{table}' no existe en la base de datos")
        
        print("[OK] Todas las tablas verificadas correctamente")
    
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
        tools_menu.add_command(label="Capturar Pestañas (Alta Calidad)", command=self.capturar_pestanas_alta_calidad)
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
        
        # Header con título
        header_frame = tk.Frame(main_frame, bg='#1E3A5F', height=80)
        header_frame.pack(fill='x', pady=(0, 10))
        header_frame.pack_propagate(False)
        
        # Título centrado en el header
        title_label = tk.Label(
            header_frame,
            text="Sistema de Gestión de Préstamos",
            font=('Segoe UI', 24, 'bold'),
            bg='#1E3A5F',
            fg='#FFD700'
        )
        title_label.pack(expand=True, pady=20)
        
        # Barra de estado con estilo personalizado
        self.status_bar = ttk.Label(
            main_frame, 
            text="Sistema de Gestión de Préstamos - Listo",
            relief='flat',
            anchor='w',
            style='Status.TLabel'
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
            self.notebook.add(self.clientes_window, text="Clientes")
            print("[OK] Pestaña de Clientes creada")
        except Exception as e:
            print(f"[ERROR] Error al crear pestaña de Clientes: {e}")
            # Crear pestaña de error
            error_frame = ttk.Frame(self.notebook)
            ttk.Label(error_frame, text=f"Error al cargar módulo de Clientes:\n{str(e)}", 
                     foreground='red').pack(pady=50)
            self.notebook.add(error_frame, text="Clientes")
    
    def create_prestamos_tab(self):
        """Crear pestaña de préstamos"""
        try:
            self.prestamos_window = PrestamosWindow(self.notebook)
            self.notebook.add(self.prestamos_window, text="Prestamos")
            print("[OK] Pestaña de Prestamos creada")
        except Exception as e:
            print(f"[ERROR] Error al crear pestaña de Prestamos: {e}")
            # Crear pestaña de error
            error_frame = ttk.Frame(self.notebook)
            ttk.Label(error_frame, text=f"Error al cargar módulo de Prestamos:\n{str(e)}", 
                     foreground='red').pack(pady=50)
            self.notebook.add(error_frame, text="Prestamos")
    
    def create_pagos_tab(self):
        """Crear pestaña de pagos"""
        try:
            self.pagos_window = PagosWindow(self.notebook)
            self.notebook.add(self.pagos_window, text="Pagos")
            print("[OK] Pestaña de Pagos creada")
        except Exception as e:
            print(f"[ERROR] Error al crear pestaña de Pagos: {e}")
            # Crear pestaña de error
            error_frame = ttk.Frame(self.notebook)
            ttk.Label(error_frame, text=f"Error al cargar módulo de Pagos:\n{str(e)}", 
                     foreground='red').pack(pady=50)
            self.notebook.add(error_frame, text="Pagos")
    
    def create_reportes_tab(self):
        """Crear pestaña de reportes"""
        try:
            self.reportes_window = ReportesWindow(self.notebook)
            self.notebook.add(self.reportes_window, text="Reportes")
            print("[OK] Pestaña de Reportes creada")
        except Exception as e:
            print(f"[ERROR] Error al crear pestaña de Reportes: {e}")
            # Crear pestaña de error
            error_frame = ttk.Frame(self.notebook)
            ttk.Label(error_frame, text=f"Error al cargar módulo de Reportes:\n{str(e)}", 
                     foreground='red').pack(pady=50)
            self.notebook.add(error_frame, text="Reportes")
    
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
        self.root.bind('<Control-Shift-C>', lambda e: self.capturar_pestanas_alta_calidad())
    
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
            
            welcome_text = f"Bienvenido al Sistema de Gestion de Prestamos\n\n" \
                          f"Estado actual:\n" \
                          f"   Clientes registrados: {num_clientes}\n" \
                          f"   Prestamos activos: {num_prestamos_activos}\n\n" \
                          f"Consejo: Usa Ctrl+N para nuevo cliente, Ctrl+P para nuevo prestamo"
            
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
            
            resumen = f"RESUMEN GENERAL\n\n" \
                     f"Total de Clientes: {total_clientes}\n" \
                     f"Total de Prestamos: {total_prestamos}\n" \
                     f"Prestamos Activos: {prestamos_activos}\n" \
                     f"Monto Total Prestado: ${total_prestado:,.2f}"
            
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

    def capturar_pestanas_alta_calidad(self):
        """Capturar pestañas principales y exportar versión lista para lona"""
        if not PIL_AVAILABLE:
            messagebox.showerror(
                "Pillow no disponible",
                "No se puede capturar la pantalla porque Pillow no está instalado.\n"
                "Instala con: pip install Pillow"
            )
            return

        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(base_dir, 'capturas')
            os.makedirs(output_dir, exist_ok=True)
            raw_dir = os.path.join(output_dir, 'raw')
            print_dir = os.path.join(output_dir, 'lona_60x40_200dpi')
            os.makedirs(raw_dir, exist_ok=True)
            os.makedirs(print_dir, exist_ok=True)

            # 60x40 cm @ 200 DPI ~= 4724 x 3150 px
            target_size = (4724, 3150)
            target_dpi = (200, 200)

            # Solo capturamos las pestañas solicitadas para presentación.
            targets = [
                ("Clientes", "clientes"),
                ("Prestamos", "prestamos"),
                ("Reportes", "reportes"),
            ]

            selected_before = self.notebook.select()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            capturas_raw = []
            capturas_print = []

            for tab_text, file_tag in targets:
                tab_idx = self._find_tab_index_by_text(tab_text)
                if tab_idx is None:
                    continue

                self.notebook.select(tab_idx)
                self.root.update_idletasks()
                self.root.update()
                time.sleep(0.2)

                x = self.root.winfo_rootx()
                y = self.root.winfo_rooty()
                w = self.root.winfo_width()
                h = self.root.winfo_height()

                image = ImageGrab.grab(bbox=(x, y, x + w, y + h))
                raw_path = os.path.join(raw_dir, f"{timestamp}_{file_tag}_raw.png")
                print_path = os.path.join(print_dir, f"{timestamp}_{file_tag}_lona_60x40_200dpi.png")
                image.save(raw_path, "PNG")

                print_image = self._prepare_image_for_print(image, target_size=target_size)
                print_image.save(print_path, "PNG", dpi=target_dpi, optimize=True)

                capturas_raw.append(raw_path)
                capturas_print.append(print_path)

            # Regresar a la pestaña que estaba activa antes.
            if selected_before:
                self.notebook.select(selected_before)
                self.root.update_idletasks()
                self.root.update()

            if capturas_print:
                messagebox.showinfo(
                    "Capturas generadas",
                    "Listo. Se generaron imágenes para impresión en lona.\n\n"
                    f"RAW: {raw_dir}\n"
                    f"IMPRESION 60x40 (200 DPI): {print_dir}\n\n"
                    f"Archivos RAW: {len(capturas_raw)}\n"
                    f"Archivos impresión: {len(capturas_print)}"
                )
            else:
                messagebox.showwarning(
                    "Sin capturas",
                    "No se encontraron las pestañas solicitadas para capturar."
                )

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron generar las capturas:\n{e}")

    def _prepare_image_for_print(self, image, target_size):
        """Ajustar imagen a tamaño de impresión manteniendo proporción"""
        src_w, src_h = image.size
        dst_w, dst_h = target_size

        scale = min(dst_w / src_w, dst_h / src_h)
        new_w = max(1, int(src_w * scale))
        new_h = max(1, int(src_h * scale))

        resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Un enfoque suave mejora la lectura de texto en impresión de gran formato.
        resized = resized.filter(ImageFilter.UnsharpMask(radius=1.2, percent=125, threshold=2))

        canvas = Image.new("RGB", (dst_w, dst_h), color="white")
        left = (dst_w - new_w) // 2
        top = (dst_h - new_h) // 2
        canvas.paste(resized, (left, top))
        return canvas

    def _find_tab_index_by_text(self, tab_text):
        """Buscar índice de pestaña por etiqueta visible"""
        for idx in range(self.notebook.index("end")):
            if self.notebook.tab(idx, "text").strip().lower() == tab_text.strip().lower():
                return idx
        return None
    
    def respaldar_db(self):
        """Respaldar base de datos"""
        try:
            # Obtener ruta de la base de datos
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_dir = os.path.join(base_dir, 'database')
            db_path = os.path.join(db_dir, 'prestamos.db')
            
            if not os.path.exists(db_path):
                messagebox.showerror("Error", "No se encontró la base de datos")
                return
            
            # Cerrar conexión activa si existe
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
            
            # Crear directorio de backups si no existe
            backups_dir = os.path.join(base_dir, 'backups')
            os.makedirs(backups_dir, exist_ok=True)
            
            # Generar nombre de archivo con fecha y hora
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'prestamos_backup_{timestamp}.db'
            default_backup_path = os.path.join(backups_dir, backup_filename)
            
            # Diálogo para seleccionar ubicación del backup
            backup_path = filedialog.asksaveasfilename(
                title="Guardar Respaldo de Base de Datos",
                defaultextension=".db",
                filetypes=[("Archivos de Base de Datos", "*.db"), ("Todos los archivos", "*.*")],
                initialdir=backups_dir,
                initialfile=backup_filename
            )
            
            if not backup_path:
                # Usuario canceló
                # Reconectar a la base de datos
                self.setup_database()
                return
            
            # Copiar archivo de base de datos
            shutil.copy2(db_path, backup_path)
            
            # Obtener tamaño del archivo
            file_size = os.path.getsize(backup_path)
            size_mb = file_size / (1024 * 1024)
            
            # Reconectar a la base de datos
            self.setup_database()
            
            messagebox.showinfo(
                "Respaldo Exitoso",
                f"La base de datos se ha respaldado correctamente.\n\n"
                f"Ubicación: {backup_path}\n"
                f"Tamaño: {size_mb:.2f} MB\n"
                f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            print(f"[OK] Respaldo creado: {backup_path}")
            
        except Exception as e:
            # Reconectar a la base de datos en caso de error
            try:
                self.setup_database()
            except:
                pass
            
            messagebox.showerror("Error", f"Error al respaldar la base de datos:\n{str(e)}")
            print(f"[ERROR] Error al respaldar: {e}")
    
    def restaurar_db(self):
        """Restaurar base de datos desde un backup"""
        try:
            # Confirmar restauración (operación peligrosa)
            respuesta = messagebox.askyesno(
                "Confirmar Restauración",
                "ADVERTENCIA: Esta operación reemplazará la base de datos actual con el backup seleccionado.\n\n"
                "Todos los datos actuales se perderán si no están en el backup.\n\n"
                "¿Estás seguro de que quieres continuar?",
                icon='warning'
            )
            
            if not respuesta:
                return
            
            # Obtener ruta de la base de datos actual
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_dir = os.path.join(base_dir, 'database')
            db_path = os.path.join(db_dir, 'prestamos.db')
            
            # Diálogo para seleccionar archivo de backup
            backup_path = filedialog.askopenfilename(
                title="Seleccionar Archivo de Respaldo",
                filetypes=[("Archivos de Base de Datos", "*.db"), ("Todos los archivos", "*.*")],
                initialdir=os.path.join(base_dir, 'backups')
            )
            
            if not backup_path:
                return
            
            if not os.path.exists(backup_path):
                messagebox.showerror("Error", "El archivo de respaldo seleccionado no existe")
                return
            
            # Verificar que el archivo sea válido (intentar conectarse)
            try:
                test_conn = sqlite3.connect(backup_path)
                test_cursor = test_conn.cursor()
                # Verificar que tenga las tablas necesarias
                test_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('clientes', 'prestamos', 'pagos')")
                tables = test_cursor.fetchall()
                test_conn.close()
                
                if len(tables) < 3:
                    messagebox.showerror(
                        "Error",
                        "El archivo de respaldo no parece ser válido.\n"
                        "No contiene todas las tablas necesarias."
                    )
                    return
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"El archivo de respaldo no es válido:\n{str(e)}")
                return
            
            # Cerrar conexión activa
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
            
            # Crear backup de la base de datos actual antes de restaurar
            if os.path.exists(db_path):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_actual = os.path.join(db_dir, f'prestamos_antes_restauracion_{timestamp}.db')
                shutil.copy2(db_path, backup_actual)
                print(f"[INFO] Backup de BD actual guardado en: {backup_actual}")
            
            # Restaurar desde el backup
            shutil.copy2(backup_path, db_path)
            
            # Reconectar a la base de datos
            self.setup_database()
            
            # Obtener información del backup
            backup_size = os.path.getsize(backup_path)
            size_mb = backup_size / (1024 * 1024)
            backup_date = datetime.fromtimestamp(os.path.getmtime(backup_path)).strftime('%Y-%m-%d %H:%M:%S')
            
            messagebox.showinfo(
                "Restauración Exitosa",
                f"La base de datos se ha restaurado correctamente desde el backup.\n\n"
                f"Archivo restaurado: {os.path.basename(backup_path)}\n"
                f"Tamaño: {size_mb:.2f} MB\n"
                f"Fecha del backup: {backup_date}\n\n"
                f"La aplicación se reiniciará para aplicar los cambios."
            )
            
            print(f"[OK] Base de datos restaurada desde: {backup_path}")
            
            # Reiniciar aplicación
            self.root.after(1000, self.reiniciar_aplicacion)
            
        except Exception as e:
            # Reconectar a la base de datos en caso de error
            try:
                self.setup_database()
            except:
                pass
            
            messagebox.showerror("Error", f"Error al restaurar la base de datos:\n{str(e)}")
            print(f"[ERROR] Error al restaurar: {e}")
    
    def reiniciar_aplicacion(self):
        """Reiniciar la aplicación para aplicar cambios de restauración"""
        try:
            # Cerrar conexión
            if self.db_connection:
                self.db_connection.close()
            
            # Reiniciar
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo reiniciar la aplicación:\n{str(e)}")
            print(f"[ERROR] Error al reiniciar: {e}")
    
    def mostrar_configuracion(self):
        """Mostrar ventana de configuración"""
        try:
            from src.config import cargar_configuracion, guardar_configuracion
            
            # Crear ventana de configuración
            config_window = tk.Toplevel(self.root)
            config_window.title("Configuración del Sistema")
            config_window.geometry("500x300")
            config_window.transient(self.root)
            config_window.grab_set()
            
            # Centrar ventana
            config_window.update_idletasks()
            x = (config_window.winfo_screenwidth() // 2) - (config_window.winfo_width() // 2)
            y = (config_window.winfo_screenheight() // 2) - (config_window.winfo_height() // 2)
            config_window.geometry(f"+{x}+{y}")
            
            # Frame principal
            main_frame = ttk.Frame(config_window, padding="20")
            main_frame.pack(fill='both', expand=True)
            
            # Título
            ttk.Label(main_frame, text="Configuración del Sistema", 
                     font=('Arial', 14, 'bold')).pack(pady=(0, 20))
            
            # Cargar configuración actual
            config = cargar_configuracion()
            
            # Frame para información del prestamista
            prestamista_frame = ttk.LabelFrame(main_frame, text="Información del Prestamista", padding="10")
            prestamista_frame.pack(fill='x', pady=10)
            
            # Nombre del prestamista
            ttk.Label(prestamista_frame, text="Nombre del Prestamista:").grid(row=0, column=0, sticky='w', pady=5)
            nombre_var = tk.StringVar(value=config.get('prestamista_nombre', ''))
            nombre_entry = ttk.Entry(prestamista_frame, textvariable=nombre_var, width=30)
            nombre_entry.grid(row=0, column=1, sticky='ew', padx=(10, 0), pady=5)
            
            # Teléfono
            ttk.Label(prestamista_frame, text="Teléfono:").grid(row=1, column=0, sticky='w', pady=5)
            telefono_var = tk.StringVar(value=config.get('prestamista_telefono', ''))
            telefono_entry = ttk.Entry(prestamista_frame, textvariable=telefono_var, width=30)
            telefono_entry.grid(row=1, column=1, sticky='ew', padx=(10, 0), pady=5)
            
            # Dirección
            ttk.Label(prestamista_frame, text="Dirección:").grid(row=2, column=0, sticky='w', pady=5)
            direccion_var = tk.StringVar(value=config.get('prestamista_direccion', ''))
            direccion_entry = ttk.Entry(prestamista_frame, textvariable=direccion_var, width=30)
            direccion_entry.grid(row=2, column=1, sticky='ew', padx=(10, 0), pady=5)
            
            prestamista_frame.columnconfigure(1, weight=1)
            
            # Frame para botones
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill='x', pady=(20, 0))
            
            def guardar():
                """Guardar configuración"""
                try:
                    nueva_config = {
                        'prestamista_nombre': nombre_var.get(),
                        'prestamista_telefono': telefono_var.get(),
                        'prestamista_direccion': direccion_var.get()
                    }
                    guardar_configuracion(nueva_config)
                    messagebox.showinfo("Éxito", "Configuración guardada correctamente", parent=config_window)
                    config_window.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"Error al guardar configuración: {e}", parent=config_window)
            
            ttk.Button(button_frame, text="Guardar", command=guardar).pack(side='right', padx=(5, 0))
            ttk.Button(button_frame, text="Cancelar", command=config_window.destroy).pack(side='right')
            
            # Enfocar en el campo de nombre
            nombre_entry.focus()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir configuración: {e}")
    
    def mostrar_manual(self):
        """Mostrar manual de usuario"""
        manual_text = """
MANUAL DE USUARIO - Sistema de Gestion de Prestamos

FUNCIONES PRINCIPALES:

GESTION DE CLIENTES:
• Agregar nuevos clientes
• Editar informacion existente
• Eliminar clientes (sin prestamos activos)
• Buscar clientes por nombre o telefono

GESTION DE PRESTAMOS:
• Crear nuevos prestamos
• Ver prestamos activos
• Calcular cuotas
• Generar tablas de amortizacion

GESTION DE PAGOS:
• Registrar pagos
• Ver historial de pagos
• Generar recibos
• Reportes de cobranza

ATAJOS DE TECLADO:
• Ctrl+N: Nuevo cliente
• Ctrl+P: Nuevo prestamo
• Ctrl+Q: Salir
• F1: Manual de usuario
• F5: Actualizar vista actual

REPORTES DISPONIBLES:
• Resumen general
• Prestamos activos
• Pagos del mes
        """
        messagebox.showinfo("Manual de Usuario", manual_text)
    
    def mostrar_acerca_de(self):
        """Mostrar información de la aplicación"""
        about_text = """
Sistema de Gestion de Prestamos
Version 1.0.0

Desarrollado con Python y Tkinter

Caracteristicas:
• Gestion completa de clientes
• Administracion de prestamos
• Control de pagos
• Reportes y estadisticas
• Interfaz intuitiva

Tecnologias utilizadas:
• Python 3.x
• Tkinter (GUI)
• SQLite (Base de datos)
• FPDF (Generacion de PDFs)

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
                    print("[OK] Conexion de base de datos cerrada")
                
                # Destruir ventana principal
                self.root.destroy()
                print("[OK] Aplicacion cerrada correctamente")
                
        except Exception as e:
            print(f"[ERROR] Error al cerrar aplicacion: {e}")
            self.root.destroy()

def main():
    """Función principal de la aplicación"""
    try:
        # Crear ventana principal
        root = tk.Tk()

        # Reescalado de interfaz para capturas más definidas (ideal para impresión).
        root.tk.call('tk', 'scaling', 2.3)
        
        # Configurar tema y estilos personalizados
        try:
            style = ttk.Style()
            style.theme_use('clam')
            
            # Configurar colores personalizados basados en el logo
            # Colores principales: Azul oscuro (#1E3A5F), Azul claro (#4A90E2), Dorado (#FFD700)
            azul_oscuro = '#1E3A5F'
            azul_claro = '#4A90E2'
            azul_medio = '#5BA3F5'
            dorado = '#FFD700'
            dorado_oscuro = '#FFA500'
            fondo_claro = '#F5F7FA'
            texto_oscuro = '#1E3A5F'
            
            style.configure('TFrame', background=fondo_claro)
            style.configure('TLabel', background=fondo_claro, foreground=texto_oscuro, font=('Segoe UI', 9))
            style.configure('TLabelFrame', background=fondo_claro, foreground=texto_oscuro, borderwidth=2, relief='solid')
            style.configure('TLabelFrame.Label', background=fondo_claro, foreground=azul_oscuro, font=('Segoe UI', 9, 'bold'))
            
            # Labels dentro de LabelFrames sin fondo (transparentes) - heredan del frame padre
            style.configure('Filter.TLabel', background=fondo_claro, foreground=texto_oscuro, font=('Segoe UI', 9))
            style.configure('Filter.TRadiobutton', background=fondo_claro, foreground=texto_oscuro, font=('Segoe UI', 9))
            
            # Asegurar que los frames dentro de LabelFrames también tengan el fondo correcto
            style.configure('Filter.TFrame', background=fondo_claro)
            
            # Botones con colores azul y dorado
            style.configure('TButton', font=('Segoe UI', 9), padding=6)
            style.map('TButton',
                     background=[('active', azul_medio), ('pressed', azul_oscuro)],
                     foreground=[('active', 'white'), ('pressed', 'white')])
            style.configure('TButton', background=azul_claro, foreground='white', borderwidth=0)
            
            # Botones destacados (dorado)
            style.configure('Accent.TButton', font=('Segoe UI', 9, 'bold'), padding=6)
            style.map('Accent.TButton',
                     background=[('active', '#FFE135'), ('pressed', dorado_oscuro)],
                     foreground=[('active', texto_oscuro), ('pressed', 'white')])
            style.configure('Accent.TButton', background=dorado, foreground=texto_oscuro, borderwidth=0)
            
            # Notebook (pestañas) con estilo mejorado en azul
            style.configure('TNotebook', background=fondo_claro, borderwidth=0)
            style.configure('TNotebook.Tab', 
                          background='#B0BEC5', 
                          foreground=texto_oscuro,
                          padding=[20, 10],
                          font=('Segoe UI', 10, 'bold'))
            style.map('TNotebook.Tab',
                     background=[('selected', azul_claro), ('active', azul_medio)],
                     foreground=[('selected', 'white'), ('active', 'white')],
                     expand=[('selected', [1, 1, 1, 0])])
            
            # Entry con estilo mejorado en azul
            style.configure('TEntry', fieldbackground='white', borderwidth=1, relief='solid', padding=5)
            style.map('TEntry',
                     fieldbackground=[('focus', '#E3F2FD')],
                     bordercolor=[('focus', azul_claro)])
            
            # Combobox con estilo mejorado en azul
            style.configure('TCombobox', fieldbackground='white', borderwidth=1, relief='solid', padding=5)
            style.map('TCombobox',
                     fieldbackground=[('focus', '#E3F2FD')],
                     bordercolor=[('focus', azul_claro)])
            
            # Treeview con estilo mejorado en azul
            style.configure('Treeview', 
                          background='white',
                          foreground=texto_oscuro,
                          fieldbackground='white',
                          rowheight=25,
                          font=('Segoe UI', 9))
            style.configure('Treeview.Heading',
                          background=azul_claro,
                          foreground='white',
                          font=('Segoe UI', 10, 'bold'),
                          relief='flat')
            style.map('Treeview',
                     background=[('selected', azul_medio)],
                     foreground=[('selected', 'white')])
            
            # Scrollbar con estilo mejorado
            style.configure('TScrollbar', 
                          background='#CFD8DC',
                          troughcolor='#ECEFF1',
                          borderwidth=0,
                          arrowcolor=texto_oscuro,
                          darkcolor='#CFD8DC',
                          lightcolor='#CFD8DC')
            style.map('TScrollbar',
                     background=[('active', '#90A4AE')])
            
            # Status bar con estilo mejorado en azul oscuro
            style.configure('Status.TLabel', 
                          background=azul_oscuro,
                          foreground='white',
                          font=('Segoe UI', 9),
                          padding=5)
            
        except Exception as e:
            print(f"[WARNING] Error al configurar estilos: {e}")
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
        
        print("[OK] Aplicacion iniciada correctamente")
        print("[INFO] Usa Ctrl+N para nuevo cliente, Ctrl+P para nuevo prestamo")
        
        # Iniciar loop principal
        root.mainloop()
        
    except Exception as e:
        print(f"[ERROR] Error al iniciar la aplicacion: {e}")
        messagebox.showerror("Error Fatal", f"Error al iniciar la aplicación:\n{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
