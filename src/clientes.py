#!/usr/bin/env python3
"""
Módulo de gestión de clientes con patrón MVC
Incluye interfaz gráfica, modelo de datos y controlador
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple

class ClienteModel:
    """Modelo para la gestión de datos de clientes"""
    
    def __init__(self, db_path: str = '../database/prestamos.db'):
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Obtener conexión a la base de datos"""
        return sqlite3.connect(self.db_path)
    
    def listar_clientes(self) -> List[Tuple]:
        """
        Obtener lista de todos los clientes
        
        Returns:
            Lista de tuplas con los datos de los clientes
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, nombre, telefono, direccion, fecha_registro
                    FROM clientes 
                    ORDER BY nombre
                ''')
                return cursor.fetchall()
        except sqlite3.Error as e:
            raise Exception(f"Error al listar clientes: {e}")
    
    def obtener_cliente(self, cliente_id: int) -> Optional[Tuple]:
        """
        Obtener un cliente específico por ID
        
        Args:
            cliente_id: ID del cliente
        
        Returns:
            Tupla con los datos del cliente o None si no existe
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, nombre, telefono, direccion, fecha_registro
                    FROM clientes WHERE id = ?
                ''', (cliente_id,))
                return cursor.fetchone()
        except sqlite3.Error as e:
            raise Exception(f"Error al obtener cliente: {e}")
    
    def agregar_cliente(self, nombre: str, telefono: str, direccion: str) -> int:
        """
        Agregar un nuevo cliente
        
        Args:
            nombre: Nombre del cliente
            telefono: Teléfono del cliente
            direccion: Dirección del cliente
        
        Returns:
            ID del cliente creado
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO clientes (nombre, telefono, direccion)
                    VALUES (?, ?, ?)
                ''', (nombre, telefono, direccion))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            raise Exception(f"Error al agregar cliente: {e}")
    
    def actualizar_cliente(self, cliente_id: int, nombre: str, telefono: str, direccion: str) -> bool:
        """
        Actualizar datos de un cliente
        
        Args:
            cliente_id: ID del cliente a actualizar
            nombre: Nuevo nombre
            telefono: Nuevo teléfono
            direccion: Nueva dirección
        
        Returns:
            True si se actualizó correctamente
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE clientes 
                    SET nombre = ?, telefono = ?, direccion = ?
                    WHERE id = ?
                ''', (nombre, telefono, direccion, cliente_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise Exception(f"Error al actualizar cliente: {e}")
    
    def eliminar_cliente(self, cliente_id: int) -> bool:
        """
        Eliminar un cliente
        
        Args:
            cliente_id: ID del cliente a eliminar
        
        Returns:
            True si se eliminó correctamente
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar si el cliente tiene préstamos activos
                cursor.execute('''
                    SELECT COUNT(*) FROM prestamos 
                    WHERE cliente_id = ? AND estado = 'ACTIVO'
                ''', (cliente_id,))
                
                if cursor.fetchone()[0] > 0:
                    raise Exception("No se puede eliminar un cliente con préstamos activos")
                
                cursor.execute('DELETE FROM clientes WHERE id = ?', (cliente_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise Exception(f"Error al eliminar cliente: {e}")
    
    def buscar_clientes(self, termino: str) -> List[Tuple]:
        """
        Buscar clientes por término
        
        Args:
            termino: Término de búsqueda
        
        Returns:
            Lista de clientes que coinciden con la búsqueda
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, nombre, telefono, direccion, fecha_registro
                    FROM clientes 
                    WHERE nombre LIKE ? OR telefono LIKE ?
                    ORDER BY nombre
                ''', (f'%{termino}%', f'%{termino}%'))
                return cursor.fetchall()
        except sqlite3.Error as e:
            raise Exception(f"Error al buscar clientes: {e}")
    
    def buscar_clientes_avanzado(self, termino: str, tipo: str) -> List[Tuple]:
        """
        Buscar clientes por tipo específico
        
        Args:
            termino: Término de búsqueda
            tipo: Tipo de búsqueda (nombre, telefono, direccion)
        
        Returns:
            Lista de tuplas con los clientes encontrados
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if tipo == "nombre":
                    query = "SELECT id, nombre, telefono, direccion, fecha_registro FROM clientes WHERE nombre LIKE ? ORDER BY nombre"
                elif tipo == "telefono":
                    query = "SELECT id, nombre, telefono, direccion, fecha_registro FROM clientes WHERE telefono LIKE ? ORDER BY nombre"
                elif tipo == "direccion":
                    query = "SELECT id, nombre, telefono, direccion, fecha_registro FROM clientes WHERE direccion LIKE ? ORDER BY nombre"
                else:
                    # Búsqueda general
                    query = "SELECT id, nombre, telefono, direccion, fecha_registro FROM clientes WHERE nombre LIKE ? OR telefono LIKE ? OR direccion LIKE ? ORDER BY nombre"
                    cursor.execute(query, (f'%{termino}%', f'%{termino}%', f'%{termino}%'))
                    return cursor.fetchall()
                
                cursor.execute(query, (f'%{termino}%',))
                return cursor.fetchall()
                
        except sqlite3.Error as e:
            raise Exception(f"Error al buscar clientes: {e}")
    
    def obtener_estadisticas(self) -> Dict:
        """
        Obtener estadísticas de clientes
        
        Returns:
            Diccionario con estadísticas
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total de clientes
                cursor.execute('SELECT COUNT(*) FROM clientes')
                total_clientes = cursor.fetchone()[0]
                
                # Clientes del mes actual
                current_month = datetime.now().strftime('%Y-%m')
                cursor.execute('SELECT COUNT(*) FROM clientes WHERE fecha_registro LIKE ?', (f'{current_month}%',))
                clientes_mes = cursor.fetchone()[0]
                
                # Clientes con teléfono
                cursor.execute('SELECT COUNT(*) FROM clientes WHERE telefono IS NOT NULL AND telefono != ""')
                con_telefono = cursor.fetchone()[0]
                
                # Clientes con dirección
                cursor.execute('SELECT COUNT(*) FROM clientes WHERE direccion IS NOT NULL AND direccion != ""')
                con_direccion = cursor.fetchone()[0]
                
                # Promedio de préstamos por cliente
                cursor.execute('''
                    SELECT AVG(prestamos_count) 
                    FROM (
                        SELECT COUNT(*) as prestamos_count 
                        FROM prestamos 
                        GROUP BY cliente_id
                    )
                ''')
                promedio_prestamos = cursor.fetchone()[0] or 0
                
                # Clientes con préstamos activos
                cursor.execute('''
                    SELECT COUNT(DISTINCT cliente_id) 
                    FROM prestamos 
                    WHERE estado = 'ACTIVO'
                ''')
                con_prestamos_activos = cursor.fetchone()[0]
                
                return {
                    'total_clientes': total_clientes,
                    'clientes_mes': clientes_mes,
                    'con_telefono': con_telefono,
                    'con_direccion': con_direccion,
                    'promedio_prestamos': promedio_prestamos,
                    'con_prestamos_activos': con_prestamos_activos
                }
                
        except sqlite3.Error as e:
            raise Exception(f"Error al obtener estadísticas: {e}")

class ClienteController:
    """Controlador para la lógica de negocio de clientes"""
    
    def __init__(self, model: ClienteModel):
        self.model = model
    
    def obtener_lista_clientes(self) -> List[Tuple]:
        """Obtener lista de clientes"""
        return self.model.listar_clientes()
    
    def obtener_cliente(self, cliente_id: int) -> Optional[Tuple]:
        """Obtener cliente específico"""
        return self.model.obtener_cliente(cliente_id)
    
    def crear_cliente(self, nombre: str, telefono: str, direccion: str) -> int:
        """Crear nuevo cliente con validaciones"""
        if not nombre.strip():
            raise ValueError("El nombre es obligatorio")
        
        if len(nombre.strip()) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        
        return self.model.agregar_cliente(nombre.strip(), telefono.strip(), direccion.strip())
    
    def modificar_cliente(self, cliente_id: int, nombre: str, telefono: str, direccion: str) -> bool:
        """Modificar cliente con validaciones"""
        if not nombre.strip():
            raise ValueError("El nombre es obligatorio")
        
        if len(nombre.strip()) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        
        return self.model.actualizar_cliente(cliente_id, nombre.strip(), telefono.strip(), direccion.strip())
    
    def borrar_cliente(self, cliente_id: int) -> bool:
        """Eliminar cliente con validaciones"""
        return self.model.eliminar_cliente(cliente_id)
    
    def buscar_clientes(self, termino: str) -> List[Tuple]:
        """Buscar clientes"""
        return self.model.buscar_clientes(termino)
    
    def buscar_clientes_avanzado(self, termino: str, tipo: str) -> List[Tuple]:
        """Buscar clientes por tipo específico"""
        return self.model.buscar_clientes_avanzado(termino, tipo)
    
    def obtener_estadisticas(self) -> Dict:
        """Obtener estadísticas de clientes"""
        return self.model.obtener_estadisticas()

class ClienteDialog:
    """Diálogo para agregar/editar clientes"""
    
    def __init__(self, parent, cliente_data: Optional[Tuple] = None):
        self.parent = parent
        self.cliente_data = cliente_data
        self.result = None
        
        # Crear ventana de diálogo
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Editar Cliente" if cliente_data else "Agregar Cliente")
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrar diálogo
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.crear_widgets()
        self.cargar_datos()
    
    def crear_widgets(self):
        """Crear widgets del diálogo"""
        # Frame principal
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Título
        titulo = "Editar Cliente" if self.cliente_data else "Agregar Cliente"
        ttk.Label(main_frame, text=titulo, font=('Arial', 14, 'bold')).pack(pady=(0, 20))
        
        # Frame para formulario
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill='x', pady=10)
        
        # Nombre
        ttk.Label(form_frame, text="Nombre *:").grid(row=0, column=0, sticky='w', pady=5)
        self.nombre_var = tk.StringVar()
        self.nombre_entry = ttk.Entry(form_frame, textvariable=self.nombre_var, width=30)
        self.nombre_entry.grid(row=0, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Teléfono
        ttk.Label(form_frame, text="Teléfono:").grid(row=1, column=0, sticky='w', pady=5)
        self.telefono_var = tk.StringVar()
        self.telefono_entry = ttk.Entry(form_frame, textvariable=self.telefono_var, width=30)
        self.telefono_entry.grid(row=1, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Dirección
        ttk.Label(form_frame, text="Dirección:").grid(row=2, column=0, sticky='w', pady=5)
        self.direccion_var = tk.StringVar()
        self.direccion_entry = ttk.Entry(form_frame, textvariable=self.direccion_var, width=30)
        self.direccion_entry.grid(row=2, column=1, sticky='ew', padx=(10, 0), pady=5)
        
        # Configurar expansión de columnas
        form_frame.columnconfigure(1, weight=1)
        
        # Frame para botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(20, 0))
        
        # Botones
        ttk.Button(button_frame, text="Guardar", command=self.guardar).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Cancelar", command=self.cancelar).pack(side='right')
        
        # Enfocar en el primer campo
        self.nombre_entry.focus()
        
        # Bind Enter para guardar
        self.dialog.bind('<Return>', lambda e: self.guardar())
        self.dialog.bind('<Escape>', lambda e: self.cancelar())
    
    def cargar_datos(self):
        """Cargar datos existentes si es edición"""
        if self.cliente_data:
            self.nombre_var.set(self.cliente_data[1])
            self.telefono_var.set(self.cliente_data[2] or '')
            self.direccion_var.set(self.cliente_data[3] or '')
    
    def guardar(self):
        """Guardar datos del cliente"""
        if not self.validar_datos():
            return
        
        nombre = self.nombre_var.get().strip()
        telefono = self.telefono_var.get().strip()
        direccion = self.direccion_var.get().strip()
        
        self.result = (nombre, telefono, direccion)
        self.dialog.destroy()
    
    def validar_datos(self):
        """Validar datos del formulario"""
        nombre = self.nombre_var.get().strip()
        telefono = self.telefono_var.get().strip()
        
        # Validar campos obligatorios
        if not nombre:
            messagebox.showerror("Error", "El nombre es obligatorio", parent=self.dialog)
            self.nombre_entry.focus()
            return False
        
        # Validar longitud mínima
        if len(nombre) < 2:
            messagebox.showerror("Error", "El nombre debe tener al menos 2 caracteres", parent=self.dialog)
            self.nombre_entry.focus()
            return False
        
        # Validar formato de teléfono
        if telefono and not self.validar_telefono(telefono):
            messagebox.showerror("Error", "Formato de teléfono inválido. Use: 123-456-7890 o 1234567890", parent=self.dialog)
            self.telefono_entry.focus()
            return False
        
        # Verificar duplicados (solo si es un nuevo cliente)
        if not self.cliente_data:  # Nuevo cliente
            if self.verificar_duplicado(nombre, telefono):
                messagebox.showerror("Error", "Ya existe un cliente con estos datos", parent=self.dialog)
                return False
        
        return True
    
    def validar_telefono(self, telefono: str) -> bool:
        """Validar formato de teléfono"""
        import re
        # Permitir formatos: 123-456-7890, 1234567890, (123) 456-7890
        patron = r'^(\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\(\d{3}\)\s?\d{3}[-.\s]?\d{4}|\d{10})$'
        return bool(re.match(patron, telefono))
    
    def verificar_duplicado(self, nombre: str, telefono: str) -> bool:
        """Verificar si ya existe un cliente con los mismos datos"""
        try:
            from src.clientes import ClienteModel
            model = ClienteModel()
            
            # Buscar por nombre
            clientes = model.buscar_clientes(nombre)
            if clientes:
                return True
            
            # Buscar por teléfono (si se proporcionó)
            if telefono:
                clientes = model.buscar_clientes(telefono)
                if clientes:
                    return True
            
            return False
        except Exception:
            return False
    
    def cancelar(self):
        """Cancelar operación"""
        self.result = None
        self.dialog.destroy()

class ClientesWindow(ttk.Frame):
    """Ventana principal de gestión de clientes"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # Inicializar modelo y controlador
        self.model = ClienteModel()
        self.controller = ClienteController(self.model)
        
        # Variables
        self.cliente_seleccionado = None
        
        # Crear interfaz
        self.crear_widgets()
        self.listar_clientes()
    
    def crear_widgets(self):
        """Crear widgets de la interfaz"""
        # Frame principal
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Título
        ttk.Label(main_frame, text="Gestión de Clientes", font=('Arial', 16, 'bold')).pack(pady=(0, 20))
        
        # Frame superior para filtros y botones
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill='x', pady=(0, 10))
        
        # Filtros avanzados
        filter_frame = ttk.LabelFrame(top_frame, text="Búsqueda y Filtros", padding="10")
        filter_frame.pack(side='left', fill='x', expand=True)
        
        # Primera fila de filtros
        filter_row1 = ttk.Frame(filter_frame)
        filter_row1.pack(fill='x', pady=(0, 5))
        
        ttk.Label(filter_row1, text="Buscar por:").pack(side='left', padx=(0, 5))
        self.tipo_busqueda = tk.StringVar(value="nombre")
        ttk.Radiobutton(filter_row1, text="Nombre", variable=self.tipo_busqueda, value="nombre").pack(side='left', padx=(0, 10))
        ttk.Radiobutton(filter_row1, text="Teléfono", variable=self.tipo_busqueda, value="telefono").pack(side='left', padx=(0, 10))
        ttk.Radiobutton(filter_row1, text="Dirección", variable=self.tipo_busqueda, value="direccion").pack(side='left')
        
        # Segunda fila de filtros
        filter_row2 = ttk.Frame(filter_frame)
        filter_row2.pack(fill='x')
        
        ttk.Label(filter_row2, text="Término:").pack(side='left', padx=(0, 5))
        self.busqueda_var = tk.StringVar()
        self.busqueda_entry = ttk.Entry(filter_row2, textvariable=self.busqueda_var, width=40)
        self.busqueda_entry.pack(side='left', padx=(0, 10))
        
        ttk.Button(filter_row2, text="🔍 Buscar", command=self.buscar_clientes).pack(side='left', padx=(0, 5))
        ttk.Button(filter_row2, text="🔄 Limpiar", command=self.limpiar_busqueda).pack(side='left', padx=(0, 5))
        ttk.Button(filter_row2, text="📊 Estadísticas", command=self.mostrar_estadisticas).pack(side='left')
        
        # Botones principales
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side='right')
        
        ttk.Button(button_frame, text="➕ Agregar", command=self.agregar_cliente).pack(side='left', padx=5)
        ttk.Button(button_frame, text="✏️ Editar", command=self.editar_cliente).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🗑️ Eliminar", command=self.eliminar_cliente).pack(side='left', padx=5)
        
        # Frame para la tabla
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill='both', expand=True)
        
        # Crear Treeview
        columns = ('ID', 'Nombre', 'Teléfono', 'Dirección', 'Fecha Registro')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Configurar columnas
        self.tree.heading('ID', text='ID')
        self.tree.heading('Nombre', text='Nombre')
        self.tree.heading('Teléfono', text='Teléfono')
        self.tree.heading('Dirección', text='Dirección')
        self.tree.heading('Fecha Registro', text='Fecha Registro')
        
        self.tree.column('ID', width=50, anchor='center')
        self.tree.column('Nombre', width=200)
        self.tree.column('Teléfono', width=120)
        self.tree.column('Dirección', width=250)
        self.tree.column('Fecha Registro', width=120, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Empaquetar tabla y scrollbar
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind eventos
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        self.tree.bind('<Double-1>', lambda e: self.editar_cliente())
        
        # Bind búsqueda con Enter
        self.busqueda_entry.bind('<Return>', lambda e: self.buscar_clientes())
    
    def listar_clientes(self):
        """Listar todos los clientes en la tabla"""
        try:
            # Limpiar tabla
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Obtener clientes
            clientes = self.controller.obtener_lista_clientes()
            
            # Insertar en tabla
            for cliente in clientes:
                self.tree.insert('', 'end', values=cliente)
            
            # Actualizar estado
            self.actualizar_estado()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al listar clientes: {e}")
    
    def agregar_cliente(self):
        """Abrir diálogo para agregar cliente"""
        dialog = ClienteDialog(self)
        self.wait_window(dialog.dialog)
        
        if dialog.result:
            try:
                nombre, telefono, direccion = dialog.result
                self.controller.crear_cliente(nombre, telefono, direccion)
                messagebox.showinfo("Éxito", "Cliente agregado correctamente")
                self.listar_clientes()
            except Exception as e:
                messagebox.showerror("Error", str(e))
    
    def editar_cliente(self):
        """Abrir diálogo para editar cliente"""
        if not self.cliente_seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un cliente para editar")
            return
        
        try:
            cliente_id = self.cliente_seleccionado[0]
            cliente_data = self.controller.obtener_cliente(cliente_id)
            
            if cliente_data:
                dialog = ClienteDialog(self, cliente_data)
                self.wait_window(dialog.dialog)
                
                if dialog.result:
                    nombre, telefono, direccion = dialog.result
                    self.controller.modificar_cliente(cliente_id, nombre, telefono, direccion)
                    messagebox.showinfo("Éxito", "Cliente actualizado correctamente")
                    self.listar_clientes()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al editar cliente: {e}")
    
    def eliminar_cliente(self):
        """Eliminar cliente seleccionado"""
        if not self.cliente_seleccionado:
            messagebox.showwarning("Advertencia", "Selecciona un cliente para eliminar")
            return
        
        try:
            cliente_id = self.cliente_seleccionado[0]
            nombre = self.cliente_seleccionado[1]
            
            # Confirmar eliminación
            respuesta = messagebox.askyesno(
                "Confirmar Eliminación",
                f"¿Estás seguro de que quieres eliminar al cliente '{nombre}'?\n\nEsta acción no se puede deshacer."
            )
            
            if respuesta:
                self.controller.borrar_cliente(cliente_id)
                messagebox.showinfo("Éxito", "Cliente eliminado correctamente")
                self.listar_clientes()
        
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def buscar_clientes(self):
        """Buscar clientes por término y tipo"""
        termino = self.busqueda_var.get().strip()
        tipo = self.tipo_busqueda.get()
        
        if termino:
            clientes = self.controller.buscar_clientes_avanzado(termino, tipo)
            self.actualizar_tabla(clientes)
            # Mostrar resultado de búsqueda
            if clientes:
                messagebox.showinfo("Búsqueda", f"Se encontraron {len(clientes)} cliente(s) con '{termino}' en {tipo}")
            else:
                messagebox.showinfo("Búsqueda", f"No se encontraron clientes con '{termino}' en {tipo}")
        else:
            self.listar_clientes()
    
    def mostrar_estadisticas(self):
        """Mostrar estadísticas de clientes"""
        try:
            stats = self.controller.obtener_estadisticas()
            
            stats_text = f"""📊 ESTADÍSTICAS DE CLIENTES

👥 Total de clientes: {stats['total_clientes']}
📅 Clientes registrados este mes: {stats['clientes_mes']}
📞 Clientes con teléfono: {stats['con_telefono']}
📍 Clientes con dirección: {stats['con_direccion']}
📈 Promedio de préstamos por cliente: {stats['promedio_prestamos']:.1f}
💰 Clientes con préstamos activos: {stats['con_prestamos_activos']}"""
            
            messagebox.showinfo("Estadísticas de Clientes", stats_text)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al obtener estadísticas: {e}")
            return
        
        try:
            # Limpiar tabla
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Buscar clientes
            clientes = self.controller.buscar_clientes(termino)
            
            # Insertar resultados
            for cliente in clientes:
                self.tree.insert('', 'end', values=cliente)
            
            # Actualizar estado
            self.actualizar_estado()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar clientes: {e}")
    
    def limpiar_busqueda(self):
        """Limpiar búsqueda y mostrar todos los clientes"""
        self.busqueda_var.set('')
        self.listar_clientes()
    
    def actualizar_tabla(self, clientes: List[Tuple]):
        """Actualizar tabla con lista de clientes específica"""
        try:
            # Limpiar tabla
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Insertar clientes en tabla
            for cliente in clientes:
                self.tree.insert('', 'end', values=cliente)
            
            # Actualizar estado
            self.actualizar_estado()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al actualizar tabla: {e}")
    
    def on_select(self, event):
        """Manejar selección de cliente"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            self.cliente_seleccionado = item['values']
        else:
            self.cliente_seleccionado = None
        
        self.actualizar_estado()
    
    def actualizar_estado(self):
        """Actualizar estado de botones según selección"""
        tiene_seleccion = self.cliente_seleccionado is not None
        tiene_clientes = len(self.tree.get_children()) > 0
        
        # Habilitar/deshabilitar botones según contexto
        for child in self.winfo_children():
            if isinstance(child, ttk.Frame):
                for button in child.winfo_children():
                    if isinstance(button, ttk.Frame):
                        for btn in button.winfo_children():
                            if isinstance(btn, ttk.Button):
                                if "Editar" in btn['text'] or "Eliminar" in btn['text']:
                                    btn['state'] = 'normal' if tiene_seleccion else 'disabled'

# Funciones de conveniencia para uso directo
def crear_cliente(nombre: str, telefono: str = '', direccion: str = '') -> int:
    """Función de conveniencia para crear un cliente"""
    model = ClienteModel()
    controller = ClienteController(model)
    return controller.crear_cliente(nombre, telefono, direccion)

def listar_clientes() -> List[Tuple]:
    """Función de conveniencia para listar clientes"""
    model = ClienteModel()
    return model.listar_clientes()

def obtener_cliente(cliente_id: int) -> Optional[Tuple]:
    """Función de conveniencia para obtener un cliente"""
    model = ClienteModel()
    return model.obtener_cliente(cliente_id)
