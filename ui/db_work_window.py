# ui/db_work_window.py - Окно работы с базой данных
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
from datetime import datetime
import os

from config import Config
from utils.helpers import validate_email

class DatabaseWorkWindow:
    def __init__(self, parent, db_client, logger):
        self.parent = parent
        self.db_client = db_client
        self.logger = logger
        
        self.window = tk.Toplevel(parent)
        self.window.title("Работа с базой данных")
        self.window.geometry("1100x750")
        self.window.resizable(True, True)
        
        # Захватываем фокус
        self.window.grab_set()
        self.window.transient(parent)

        # Центрируем окно
        self.center_window()
        
        # Переменные
        self.search_email_var = tk.StringVar()
        self.search_client_id_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Готов к работе")
        
        # Результаты поиска
        self.current_results = []
        
        # Настройка интерфейса
        self.setup_ui()
        
        # Фокус на поле ввода
        self.window.after(100, lambda: self.email_entry.focus_set())
    
    def center_window(self):
        """Центрирует окно на экране"""
        self.window.update_idletasks()
        
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        window_width = 1100
        window_height = 750
        
        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2
        
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def setup_ui(self):
        """Настраивает пользовательский интерфейс"""
        # Основной контейнер
        main_container = ttk.PanedWindow(self.window, orient=tk.VERTICAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Верхняя панель - поиск
        search_panel = ttk.Frame(main_container)
        main_container.add(search_panel, weight=1)
        
        # Нижняя панель - результаты
        results_panel = ttk.Frame(main_container)
        main_container.add(results_panel, weight=3)
        
        # ===== ПАНЕЛЬ ПОИСКА =====
        self.setup_search_panel(search_panel)
        
        # ===== ПАНЕЛЬ РЕЗУЛЬТАТОВ =====
        self.setup_results_panel(results_panel)
    
    def setup_search_panel(self, parent):
        """Настраивает панель поиска"""
        # Контейнер вкладок для разных типов поиска
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Вкладка: Поиск по email
        email_tab = ttk.Frame(notebook)
        notebook.add(email_tab, text="📧 Поиск по Email")
        
        # Вкладка: Проверка документов
        docs_tab = ttk.Frame(notebook)
        notebook.add(docs_tab, text="📄 Проверка документов")
        
        # ===== ВКЛАДКА EMAIL =====
        self.setup_email_tab(email_tab)
        
        # ===== ВКЛАДКА ДОКУМЕНТЫ =====
        self.setup_docs_tab(docs_tab)
    
    def setup_email_tab(self, parent):
        """Настраивает вкладку поиска по email"""
        frame = ttk.Frame(parent, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        tk.Label(
            frame,
            text="Поиск клиента по email адресу",
            font=("Arial", 14, "bold"),
            foreground="#2c3e50"
        ).pack(pady=(0, 20))
        
        # Поле ввода email
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(input_frame, text="Email адрес:", font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 10))
        
        self.email_entry = ttk.Entry(
            input_frame,
            textvariable=self.search_email_var,
            width=50,
            font=("Arial", 11)
        )
        self.email_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Подсказка
        tk.Label(
            input_frame,
            text="Пример: client@example.com",
            font=("Arial", 9),
            foreground="#7f8c8d"
        ).pack(side=tk.LEFT)
        
        # Кнопка поиска
        search_btn = tk.Button(
            frame,
            text="🔍 Найти клиента",
            command=lambda: self.search_by_email(self.search_email_var.get())
        )
        search_btn.config(
            background="#3498db",
            foreground="white",
            font=("Arial", 12, "bold"),
            relief="flat",
            padx=30,
            pady=12,
            cursor="hand2"
        )
        search_btn.pack(pady=(0, 10))
        
        # Привязываем Enter к поиску
        self.email_entry.bind('<Return>', lambda e: self.search_by_email(self.search_email_var.get()))
        
        # Кнопка для поиска типов документов
        find_types_btn = tk.Button(
            frame,
            text="🔎 Найти типы документов",
            command=self.find_document_types
        )
        find_types_btn.config(
            background="#9b59b6",
            foreground="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2"
        )
        find_types_btn.pack(pady=(10, 0))
        
        # Статус поиска
        self.email_status_label = tk.Label(
            frame,
            text="Введите email для поиска",
            font=("Arial", 10),
            foreground="#7f8c8d"
        )
        self.email_status_label.pack()
    
    def setup_docs_tab(self, parent):
        """Настраивает вкладку проверки документов"""
        frame = ttk.Frame(parent, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        tk.Label(
            frame,
            text="Проверка документов клиента",
            font=("Arial", 14, "bold"),
            foreground="#2c3e50"
        ).pack(pady=(0, 20))
        
        # Описание
        tk.Label(
            frame,
            text="Проверяет наличие документов для указанного клиента\nПоиск в таблицах: pto_ts_own и других с полями id, demand_id",
            font=("Arial", 10),
            foreground="#7f8c8d",
            wraplength=600
        ).pack(pady=(0, 20))
        
        # Поле ввода ID клиента
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(input_frame, text="ID клиента:", font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 10))
        
        self.client_id_entry = ttk.Entry(
            input_frame,
            textvariable=self.search_client_id_var,
            width=30,
            font=("Arial", 11)
        )
        self.client_id_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Кнопка проверки
        check_btn = tk.Button(
            frame,
            text="🔍 Проверить документы",
            command=lambda: self.check_documents(self.search_client_id_var.get())
        )
        check_btn.config(
            background="#2ecc71",
            foreground="white",
            font=("Arial", 12, "bold"),
            relief="flat",
            padx=30,
            pady=12,
            cursor="hand2"
        )
        check_btn.pack(pady=(0, 10))
        
        # Привязываем Enter к поиску
        self.client_id_entry.bind('<Return>', lambda e: self.check_documents(self.search_client_id_var.get()))
        
        # Область для результатов проверки документов
        self.docs_result_text = scrolledtext.ScrolledText(
            frame,
            wrap=tk.WORD,
            height=10,
            font=("DejaVu Sans Mono", 10)
        )
        self.docs_result_text.config(
            background="#f8f9fa",
            padx=10,
            pady=10
        )
        self.docs_result_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Статус проверки
        self.docs_status_label = tk.Label(
            frame,
            text="Введите ID клиента для проверки документов",
            font=("Arial", 10),
            foreground="#7f8c8d"
        )
        self.docs_status_label.pack()
    
    def show_notification(self, title, message, parent_window=None):
        """Показывает уведомление в текущем окне без потери фокуса"""
        if parent_window is None:
            parent_window = self.window
        
        # Создаем небольшое окно уведомления
        notif_window = tk.Toplevel(parent_window)
        notif_window.title(title)
        notif_window.geometry("300x150")
        notif_window.resizable(False, False)
        
        # Делаем его модальным
        notif_window.grab_set()
        notif_window.transient(parent_window)
        
        # Центрируем относительно родительского окна
        notif_window.update_idletasks()
        x = parent_window.winfo_x() + (parent_window.winfo_width() - 300) // 2
        y = parent_window.winfo_y() + (parent_window.winfo_height() - 150) // 2
        notif_window.geometry(f"300x150+{x}+{y}")
        
        # Текст сообщения
        tk.Label(notif_window, text=message, font=("Arial", 11), 
                wraplength=250, justify="center").pack(pady=20)
        
        # Кнопка ОК
        tk.Button(notif_window, text="OK", width=10,
                command=notif_window.destroy).pack(pady=10)
        
        # Фокус на кнопке OK при нажатии Enter
        notif_window.bind('<Return>', lambda e: notif_window.destroy())
    
    def setup_results_panel(self, parent):
        """Настраивает панель результатов"""
        # Основной фрейм
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Панель инструментов
        toolbar = tk.Frame(main_frame, bg="#f0f0f0", height=40)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)
        
        # Кнопки управления результатами
        toolbar_buttons = [
            ("🗑️ Очистить", self.clear_results, "#e74c3c"),
            ("📋 Копировать ID", self.copy_selected_id, "#3498db"),
            ("📋 Копировать все ID", self.copy_all_ids, "#3498db"),
            ("📋 Копировать строку", self.copy_selected_row, "#9b59b6"),
            ("💾 Экспорт", self.export_results, "#2ecc71"),
            ("📊 Подробнее", self.show_details, "#f39c12")
        ]
        
        for text, command, color in toolbar_buttons:
            btn = tk.Button(toolbar, text=text, command=command)
            btn.config(
                background=color,
                foreground="white",
                relief="flat",
                padx=15,
                pady=5,
                cursor="hand2"
            )
            btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        # Статистика
        self.stats_label = tk.Label(
            toolbar,
            text="Найдено: 0 записей",
            font=("Arial", 10, "bold"),
            bg="#f0f0f0"
        )
        self.stats_label.pack(side=tk.RIGHT, padx=10)
        
        # Область для результатов
        results_frame = ttk.Frame(main_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Дерево для отображения результатов
        columns = ('ID', 'ФИО', 'Email', 'Телефон', 'Дата создания')
        
        self.results_tree = ttk.Treeview(
            results_frame,
            columns=columns,
            show='headings',
            selectmode='extended'
        )
        
        # Настраиваем колонки
        column_widths = [80, 200, 250, 150, 120]
        for col, width in zip(columns, column_widths):
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=width, minwidth=50)
        
        # Добавляем вертикальную прокрутку
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        # Размещаем элементы
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Контекстное меню
        self.create_context_menu()
        
        # Панель статуса
        status_frame = tk.Frame(main_frame, height=25, bg="#e8e8e8")
        status_frame.pack(fill=tk.X, pady=(5, 0))
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg="#e8e8e8",
            anchor=tk.W,
            padx=10
        )
        self.status_label.pack(fill=tk.X)
    
    def create_context_menu(self):
        """Создает контекстное меню для дерева результатов"""
        self.context_menu = tk.Menu(self.results_tree, tearoff=0)
        self.context_menu.add_command(label="Копировать ID", command=self.copy_selected_id)
        self.context_menu.add_command(label="Копировать все ID", command=self.copy_all_ids)
        self.context_menu.add_command(label="Копировать строку", command=self.copy_selected_row)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Показать подробности", command=self.show_selected_details)
        
        # Привязываем меню
        self.results_tree.bind("<Button-3>", self.show_context_menu)
    
    def show_context_menu(self, event):
        """Показывает контекстное меню"""
        try:
            item = self.results_tree.identify_row(event.y)
            if item:
                self.results_tree.selection_set(item)
                self.context_menu.post(event.x_root, event.y_root)
        except:
            pass
    
    def find_document_types(self):
        """Ищет таблицу с типами документов"""
        self.status_var.set("Поиск таблицы с типами документов...")
        self.logger.log("Поиск таблицы с типами документов...", "INFO")
        
        threading.Thread(
            target=self._perform_document_type_search,
            daemon=True
        ).start()
    
    def _perform_document_type_search(self):
        """Выполняет поиск типов документов в отдельном потоке"""
        try:
            result = self.db_client.get_document_type_info()
            
            # Обновляем UI в главном потоке
            self.window.after(0, self._display_document_type_results, result)
            
        except Exception as e:
            self.window.after(0, self._show_document_type_error, str(e))
    
    def _display_document_type_results(self, result):
        """Отображает результаты поиска типов документов"""
        if not result:
            messagebox.showinfo("Типы документов", "Таблица с типами документов не найдена")
            self.status_var.set("Таблица с типами документов не найдена")
            return
        
        if 'table_name' in result:
            # Нашли таблицу с данными
            table_name = result['table_name']
            data = result['data']
            
            # Создаем окно для отображения результатов
            type_window = tk.Toplevel(self.window)
            type_window.title(f"Типы документов - {table_name}")
            type_window.geometry("800x600")
            
            # Центрируем окно
            type_window.update_idletasks()
            x = self.window.winfo_x() + (self.window.winfo_width() - 800) // 2
            y = self.window.winfo_y() + (self.window.winfo_height() - 600) // 2
            type_window.geometry(f"800x600+{x}+{y}")
            
            # Заголовок
            tk.Label(
                type_window,
                text=f"Таблица типов документов: {table_name}",
                font=("Arial", 14, "bold"),
                foreground="#2c3e50"
            ).pack(pady=10)
            
            # Область для текста
            text_area = scrolledtext.ScrolledText(
                type_window,
                wrap=tk.WORD,
                font=("DejaVu Sans Mono", 10)
            )
            text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Форматируем вывод
            text_area.insert(tk.END, f"{'='*80}\n")
            text_area.insert(tk.END, f"ТИПЫ ДОКУМЕНТОВ\n")
            text_area.insert(tk.END, f"Таблица: {table_name}\n")
            text_area.insert(tk.END, f"Найдено записей: {len(data)}\n")
            text_area.insert(tk.END, f"{'='*80}\n\n")
            
            for i, row in enumerate(data, 1):
                text_area.insert(tk.END, f"Запись #{i}:\n")
                text_area.insert(tk.END, f"{'-'*40}\n")
                
                for key, value in row.items():
                    if value is not None:
                        if hasattr(value, 'strftime'):
                            value = value.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            value = str(value)
                        
                        if value.strip():
                            text_area.insert(tk.END, f"{key}: {value}\n")
                
                text_area.insert(tk.END, "\n")
            
            text_area.config(state='disabled')
            self.status_var.set(f"Найдена таблица типов документов: {table_name}")
            
        elif 'tables' in result:
            # Нашли таблицы с колонками type_doc
            tables = result['tables']
            
            text = f"Найдены таблицы с колонками, содержащими 'type_doc':\n\n"
            
            current_table = ""
            for table_name, column_name in tables:
                if table_name != current_table:
                    text += f"\nТаблица: {table_name}\n"
                    text += f"Колонки:\n"
                    current_table = table_name
                
                text += f"  - {column_name}\n"
            
            messagebox.showinfo("Таблицы с type_doc", text)
            self.status_var.set(f"Найдено таблиц с type_doc: {len(set(t[0] for t in tables))}")
    
    def _show_document_type_error(self, error_message):
        """Показывает ошибку поиска типов документов"""
        messagebox.showerror("Ошибка", f"Не удалось найти типы документов: {error_message}")
        self.status_var.set("Ошибка поиска типов документов")
    
    def search_by_email(self, email):
        """Выполняет поиск клиента по email"""
        if not email or email.strip() == "":
            messagebox.showwarning("Внимание", "Введите email для поиска")
            self.email_entry.focus_set()
            return
        
        if not validate_email(email):
            if messagebox.askyesno("Подтверждение", 
                                  f"Email '{email}' не выглядит валидным.\nПродолжить поиск?"):
                pass
            else:
                self.email_entry.focus_set()
                return
        
        # Обновляем статус
        self.email_status_label.config(
            text=f"Поиск по email: {email}...",
            foreground="#f39c12"
        )
        self.status_var.set(f"Поиск по email: {email}")
        
        # Выполняем поиск в отдельном потоке
        threading.Thread(
            target=self._perform_email_search,
            args=(email.strip(),),
            daemon=True
        ).start()
    
    def _perform_email_search(self, email):
        """Выполняет поиск по email в отдельном потоке"""
        try:
            results = self.db_client.search_client_by_email(email)
            
            # Обновляем UI в главном потоке
            self.window.after(0, self._display_email_results, results, email)
            
        except Exception as e:
            self.window.after(0, self._show_search_error, "email", str(e))
    
    def check_documents(self, client_id):
        """Проверяет наличие документов у клиента"""
        if not client_id or client_id.strip() == "":
            messagebox.showwarning("Внимание", "Введите ID клиента для проверки")
            self.client_id_entry.focus_set()
            return
        
        # Проверяем, что ID - число
        try:
            int(client_id)
        except ValueError:
            messagebox.showwarning("Внимание", "ID клиента должен быть числом")
            self.client_id_entry.focus_set()
            return
        
        # Обновляем статус
        self.docs_status_label.config(
            text=f"Проверка документов для клиента ID: {client_id}...",
            foreground="#f39c12"
        )
        self.status_var.set(f"Проверка документов для клиента ID: {client_id}")
        
        # Очищаем область результатов
        self.docs_result_text.delete(1.0, tk.END)
        
        # Выполняем проверку в отдельном потоке
        threading.Thread(
            target=self._perform_document_check,
            args=(client_id.strip(),),
            daemon=True
        ).start()

    def _display_document_results(self, documents, client_id):
        """Отображает результаты проверки документов"""
        # Очищаем текст
        self.docs_result_text.delete(1.0, tk.END)
        
        # Форматируем вывод
        self.docs_result_text.insert(tk.END, f"{'='*60}\n")
        self.docs_result_text.insert(tk.END, f"ПРОВЕРКА ДОКУМЕНТОВ ДЛЯ КЛИЕНТА\n")
        self.docs_result_text.insert(tk.END, f"ID клиента: {client_id}\n")
        self.docs_result_text.insert(tk.END, f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.docs_result_text.insert(tk.END, f"{'='*60}\n\n")
        
        # Проверяем, что documents не None
        if documents is None:
            self.docs_result_text.insert(tk.END, "❌ Ошибка подключения к базе данных\n")
            self.docs_result_text.insert(tk.END, "Не удалось установить соединение с базой данных.\n")
            self.docs_status_label.config(
                text="Ошибка подключения к базе данных",
                foreground="#e74c3c"
            )
            self.status_var.set("Ошибка подключения к БД")
            return
        
        # Проверяем, что documents - список
        if not isinstance(documents, list):
            self.docs_result_text.insert(tk.END, "❌ Ошибка: неправильный формат данных\n")
            self.docs_result_text.insert(tk.END, f"Тип данных: {type(documents)}\n")
            self.docs_status_label.config(
                text="Ошибка формата данных",
                foreground="#e74c3c"
            )
            self.status_var.set("Ошибка формата данных")
            return
        
        if len(documents) == 0:
            self.docs_result_text.insert(tk.END, "❌ Документы не найдены\n\n")
            self.docs_result_text.insert(tk.END, f"Для клиента с ID {client_id} не найдено записей в базе данных.\n\n")
            self.docs_result_text.insert(tk.END, "Проверьте:\n")
            self.docs_result_text.insert(tk.END, "1. Правильность введенного ID клиента\n")
            self.docs_result_text.insert(tk.END, "2. Наличие документов у данного клиента\n")
            
            self.docs_status_label.config(
                text=f"Документы для клиента ID {client_id} не найдены",
                foreground="#e74c3c"
            )
            self.status_var.set(f"Документы не найдены для клиента ID {client_id}")
        else:
            # Отображаем найденные документы
            self.docs_result_text.insert(tk.END, f"✅ Найдено записей: {len(documents)}\n\n")
            
            for i, doc in enumerate(documents, 1):
                self.docs_result_text.insert(tk.END, f"Запись #{i}:\n")
                self.docs_result_text.insert(tk.END, f"{'-'*40}\n")
                
                # Выводим все поля документа
                for key, value in doc.items():
                    if value is not None:
                        if isinstance(value, (int, float)):
                            value_str = str(value)
                        elif hasattr(value, 'strftime'):
                            value_str = value.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            value_str = str(value)
                        
                        if value_str.strip():
                            self.docs_result_text.insert(tk.END, f"{key}: {value_str}\n")
                
                self.docs_result_text.insert(tk.END, "\n")
            
            # Пытаемся извлечь полезную информацию
            self.docs_result_text.insert(tk.END, f"{'='*60}\n")
            self.docs_result_text.insert(tk.END, f"АНАЛИЗ ДАННЫХ:\n")
            self.docs_result_text.insert(tk.END, f"{'='*60}\n\n")
            
            # Ищем ID документов
            doc_ids = []
            for doc in documents:
                # Пробуем разные поля для ID документа
                for field in ['demand_id', 'document_id', 'doc_id', 'id_document']:
                    if field in doc and doc[field] is not None:
                        doc_ids.append(str(doc[field]))
                        break
            
            if doc_ids:
                self.docs_result_text.insert(tk.END, f"Найдено ID документов: {len(doc_ids)}\n")
                self.docs_result_text.insert(tk.END, f"ID документов: {', '.join(doc_ids)}\n\n")
            
            # Ищем типы документов
            type_docs = []
            for doc in documents:
                for field in ['type_doc', 'doc_type', 'document_type', 'type']:
                    if field in doc and doc[field] is not None:
                        type_docs.append(str(doc[field]))
                        break
            
            if type_docs:
                self.docs_result_text.insert(tk.END, f"Типы документов: {', '.join(type_docs)}\n")
            
            self.docs_status_label.config(
                text=f"Найдено записей: {len(documents)} для клиента ID {client_id}",
                foreground="#27ae60"
            )
            self.status_var.set(f"Найдено записей: {len(documents)} для клиента ID {client_id}")
        
        # Прокручиваем в начало
        self.docs_result_text.see(1.0)
    
    def _perform_document_check(self, client_id):
        """Проверяет документы в отдельном потоке"""
        try:
            # Получаем документы для клиента
            documents = self.db_client.get_client_documents(client_id)
            
            # Обновляем UI в главном потоке
            self.window.after(0, self._display_document_results, documents, client_id)
            
        except Exception as e:
            self.window.after(0, self._show_document_error, str(e))
    
    def _display_email_results(self, results, email):
        """Отображает результаты поиска по email"""
        self.current_results = results
        
        if results is None:
            self.email_status_label.config(
                text="Ошибка подключения к базе данных",
                foreground="#e74c3c"
            )
            self.status_var.set("Ошибка подключения к БД")
            messagebox.showerror("Ошибка", "Не удалось подключиться к базе данных")
            return
        
        self.display_results_in_tree(results, f"Результаты поиска по email: {email}")
        
        if not results:
            self.email_status_label.config(
                text=f"Клиенты с email '{email}' не найдены",
                foreground="#e74c3c"
            )
            self.status_var.set(f"По email '{email}' клиенты не найдены")
        else:
            self.email_status_label.config(
                text=f"Найдено клиентов: {len(results)}",
                foreground="#27ae60"
            )
            self.status_var.set(f"Найдено клиентов: {len(results)}")
    
    def get_client_documents(self, client_id):
        """Получает документы клиента из таблицы one_load_history"""
        if not self.connect():
            return None
        
        try:
            cursor = self.connection.cursor(as_dict=True)
            
            # Проверяем несколько возможных таблиц с документами
            possible_tables = [
                'one_load_history',
                'pto_ts_own', 
                'documents',
                'client_documents',
                'docs',
                'demand_docs',
                'documentation',
                'dokumenty',
                'dokumentatsiya'
            ]
            
            found_table = None
            
            for table_name in possible_tables:
                cursor.execute("""
                    SELECT TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = %s
                """, (table_name,))
                
                if cursor.fetchone():
                    found_table = table_name
                    self.logger.log(f"Найдена таблица документов: {table_name}", "INFO")
                    break
            
            if not found_table:
                self.logger.log("Таблица с документами не найдена", "ERROR")
                return []
            
            # Проверяем структуру найденной таблицы
            cursor.execute(f"""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = '{found_table}'
                ORDER BY COLUMN_NAME
            """)
            
            columns = [row[0].lower() for row in cursor.fetchall()]
            self.logger.log(f"Колонки в таблице {found_table}: {columns}", "INFO")
            
            # Формируем запрос в зависимости от найденной таблицы
            if found_table == 'one_load_history':
                # Для таблицы one_load_history
                query = """
                SELECT *
                FROM one_load_history
                WHERE id = %s
                ORDER BY id
                """
            else:
                # Для других таблиц - общий запрос
                # Проверяем наличие основных колонок
                select_columns = []
                
                # Всегда включаем id
                if 'id' in columns:
                    select_columns.append("id")
                
                # Добавляем demand_id если есть
                if 'demand_id' in columns:
                    select_columns.append("demand_id")
                
                # Добавляем type_doc если есть
                if 'type_doc' in columns:
                    select_columns.append("type_doc")
                
                # Добавляем остальные колонки
                other_columns = ['num_type', 'date_add', 'created', 
                               'type_doc_adv', 'sub_type', 'currant_doc_id']
                
                for col in other_columns:
                    if col in columns:
                        select_columns.append(col)
                
                # Формируем запрос
                if not select_columns:
                    select_columns = ["*"]  # Если не нашли нужных колонок, выбираем все
                
                select_clause = ", ".join(select_columns)
                
                # Формируем WHERE условие
                where_condition = "id = %s"
                
                query = f"""
                SELECT {select_clause}
                FROM {found_table}
                WHERE {where_condition}
                ORDER BY id
                """
            
            self.logger.log(f"Выполняем запрос: {query} с client_id={client_id}", "INFO")
            cursor.execute(query, (client_id,))
            results = cursor.fetchall()
            
            self.logger.log(f"Найдено записей для клиента {client_id}: {len(results)}", "INFO")
            return results
            
        except Exception as e:
            self.logger.log(f"Ошибка получения документов: {e}", "ERROR")
            import traceback
            error_details = traceback.format_exc()
            self.logger.log(f"Детали ошибки: {error_details}", "ERROR")
            # Возвращаем пустой список при ошибке
            return []
        finally:
            self.disconnect()
    
    def copy_to_clipboard(self, text, description=""):
        """Копирует текст в буфер обмена и показывает сообщение в текущем окне"""
        try:
            self.window.clipboard_clear()
            self.window.clipboard_append(text)
            if description:
                self.show_notification("Успех", f"{description} скопированы в буфер обмена")
                self.status_var.set(f"Скопировано: {description}")
            else:
                self.show_notification("Успех", "Текст скопирован в буфер обмена")
                self.status_var.set("Текст скопирован")
        except Exception as e:
            self.show_notification("Ошибка", f"Не удалось скопировать: {e}")
            self.status_var.set("Ошибка копирования")
    
    def _show_search_error(self, search_type, error_message):
        """Показывает ошибку поиска"""
        if search_type == "email":
            self.email_status_label.config(
                text=f"Ошибка поиска: {error_message[:50]}...",
                foreground="#e74c3c"
            )
        
        self.status_var.set(f"Ошибка поиска: {error_message[:100]}...")
        self.logger.log(f"Ошибка поиска ({search_type}): {error_message}", "ERROR")
    
    def _show_document_error(self, error_message):
        """Показывает ошибку проверки документов"""
        # Очищаем область результатов
        self.docs_result_text.delete(1.0, tk.END)
        self.docs_result_text.insert(tk.END, f"Ошибка: {error_message}\n")
        
        self.docs_status_label.config(
            text=f"Ошибка проверки документов: {error_message[:50]}...",
            foreground="#e74c3c"
        )
        self.status_var.set(f"Ошибка проверки документов: {error_message[:100]}...")
        self.logger.log(f"Ошибка проверки документов: {error_message}", "ERROR")
    
    def display_results_in_tree(self, results, title=None):
        """Отображает результаты в дереве"""
        # Очищаем дерево
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Сохраняем результаты
        self.current_results = results
        
        if not results:
            self.stats_label.config(text="Найдено: 0 записей")
            self.status_var.set("Записей не найдено")
            return
        
        # Добавляем записи в дерево
        for i, row in enumerate(results, 1):
            # Извлекаем ID клиента - ПРЕОБРАЗОВЫВАЕМ В СТРОКУ
            client_id = ""
            for key in ['id', 'client_id', 'ID', 'CLIENT_ID']:
                if key in row and row[key] is not None:
                    client_id = str(row[key])
                    break
            
            # Если не нашли, используем номер строки
            if not client_id or client_id == 'None':
                client_id = str(i)
            
            # Формируем ФИО
            last_name = row.get('last_name', '')
            first_name = row.get('first_name', '')
            patronymic = row.get('patronymic', '')
            full_name = f"{last_name} {first_name} {patronymic}".strip()
            
            # Email и телефон
            email = row.get('email', '')
            phone = row.get('phone', '') or row.get('mobile_phone', '')
            
            # Дата создания
            create_date = row.get('create_date', '')
            if create_date:
                if hasattr(create_date, 'strftime'):
                    create_date = create_date.strftime('%Y-%m-%d')
            
            # Вставляем в дерево
            self.results_tree.insert('', tk.END, values=(
                client_id,
                full_name,
                email,
                phone,
                create_date
            ), tags=(str(i), client_id))  # Сохраняем ID клиента в тегах
        
        # Обновляем статистику
        self.stats_label.config(text=f"Найдено: {len(results)} записей")
        
        if title:
            self.status_var.set(title)

    def copy_to_clipboard(self, text, description=""):
        """Копирует текст в буфер обмена и показывает сообщение в текущем окне"""
        try:
            self.window.clipboard_clear()
            self.window.clipboard_append(text)
            if description:
                messagebox.showinfo("Успех", f"{description} скопированы в буфер обмена")
            else:
                messagebox.showinfo("Успех", "Текст скопирован в буфер обмена")
            self.status_var.set(f"Скопировано: {description or 'текст'}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать: {e}")
            self.status_var.set("Ошибка копирования")
    
    def clear_results(self):
        """Очищает результаты поиска"""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        self.current_results = []
        self.stats_label.config(text="Найдено: 0 записей")
        self.status_var.set("Результаты очищены")
    
    def copy_selected_id(self):
        """Копирует ID выбранной записи (только число)"""
        selected_items = self.results_tree.selection()
        if not selected_items:
            messagebox.showinfo("Информация", "Выберите строку для копирования ID")
            return
        
        try:
            ids_to_copy = []
            for item in selected_items:
                # Получаем ID из первого столбца дерева
                values = self.results_tree.item(item)['values']
                if values and len(values) > 0:
                    client_id = str(values[0])  # Первый столбец - ID
                    if client_id and client_id != 'None' and client_id != '':
                        ids_to_copy.append(client_id)
            
            if ids_to_copy:
                # Объединяем ID через запятую
                text = ', '.join(ids_to_copy)
                # Используем метод copy_to_clipboard
                self.copy_to_clipboard(text, f"ID ({len(ids_to_copy)})")
            else:
                messagebox.showinfo("Информация", "В выбранных строках нет ID")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать ID: {e}")
    
    def copy_all_ids(self):
        """Копирует все ID из результатов (только числа)"""
        if not self.current_results:
            messagebox.showinfo("Информация", "Нет данных для копирования")
            return
        
        try:
            ids_to_copy = []
            for row in self.current_results:
                # Извлекаем ID клиента из разных возможных полей
                client_id = ""
                for key in ['id', 'client_id', 'ID', 'CLIENT_ID']:
                    if key in row and row[key] is not None:
                        client_id = str(row[key])
                        break
                
                if client_id and client_id != 'None' and client_id != '':
                    ids_to_copy.append(client_id)
            
            if ids_to_copy:
                # Объединяем ID через запятую
                text = ', '.join(ids_to_copy)
                # Используем метод copy_to_clipboard
                self.copy_to_clipboard(text, f"Все ID ({len(ids_to_copy)})")
            else:
                messagebox.showinfo("Информация", "В результатах нет ID")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать ID: {e}")
    
    def copy_selected_row(self):
        """Копирует выбранную строку целиком"""
        selected_items = self.results_tree.selection()
        if not selected_items:
            messagebox.showinfo("Информация", "Выберите строку для копирования")
            return
        
        try:
            text_lines = []
            for item in selected_items:
                values = self.results_tree.item(item)['values']
                # Преобразуем все значения в строки
                str_values = [str(v) if v is not None else '' for v in values]
                text_lines.append('\t'.join(str_values))
            
            text = '\n'.join(text_lines)
            # Используем метод copy_to_clipboard
            self.copy_to_clipboard(text, f"Строки ({len(selected_items)})")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать: {e}")
    
    def export_results(self):
        """Экспортирует результаты в файл"""
        if not self.current_results:
            messagebox.showinfo("Информация", "Нет данных для экспорта")
            return
        
        try:
            # Предлагаем выбрать файл
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[
                    ("Текстовые файлы", "*.txt"),
                    ("CSV файлы", "*.csv"),
                    ("Все файлы", "*.*")
                ],
                initialfile=f"dog_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            if not filename:
                return
            
            # Формируем текст для экспорта
            text = self.format_results_for_export(filename.endswith('.csv'))
            
            # Сохраняем в файл
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(text)
            
            self.status_var.set(f"Результаты экспортированы в: {os.path.basename(filename)}")
            messagebox.showinfo("Экспорт", f"Данные экспортированы в файл:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать: {e}")
    
    def show_details(self):
        """Показывает подробную информацию о результатах"""
        if not self.current_results:
            messagebox.showinfo("Информация", "Нет данных для отображения")
            return
        
        self.show_selected_details()
    
    def show_selected_details(self):
        """Показывает подробную информацию о выбранной записи"""
        selected_items = self.results_tree.selection()
        if not selected_items:
            messagebox.showinfo("Информация", "Выберите запись для просмотра подробностей")
            return
        
        # Берем первую выбранную запись
        item = selected_items[0]
        item_index = int(self.results_tree.item(item)['tags'][0]) - 1
        
        if 0 <= item_index < len(self.current_results):
            self.show_record_details(item_index)
    
    def show_record_details(self, index):
        """Показывает детальную информацию о записи"""
        if not self.current_results or index >= len(self.current_results):
            return
        
        record = self.current_results[index]
        
        # Создаем окно с деталями
        details_window = tk.Toplevel(self.window)
        details_window.title(f"Детали записи #{index + 1}")
        details_window.geometry("700x600")
        details_window.resizable(True, True)
        
        # Центрируем окно
        details_window.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() - 700) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - 600) // 2
        details_window.geometry(f"700x600+{x}+{y}")
        
        # Основной контейнер
        main_frame = ttk.Frame(details_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        tk.Label(
            main_frame,
            text=f"Детальная информация о записи #{index + 1}",
            font=("Arial", 14, "bold"),
            foreground="#2c3e50"
        ).pack(pady=(0, 20))
        
        # Кнопка для копирования ID
        id_frame = ttk.Frame(main_frame)
        id_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Находим ID клиента
        client_id = ""
        for key in ['id', 'client_id', 'ID', 'CLIENT_ID']:
            if key in record and record[key] is not None:
                client_id = str(record[key])
                break
        
        if not client_id or client_id == 'None':
            client_id = "Не найден"
        
        tk.Label(id_frame, text=f"ID клиента: {client_id}", font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        
        if client_id != "Не найден":
            copy_id_btn = tk.Button(
                id_frame,
                text="📋 Копировать ID",
                command=lambda: self.copy_single_id(client_id)
            )
            copy_id_btn.config(
                background="#3498db",
                foreground="white",
                font=("Arial", 9),
                relief="flat",
                padx=10,
                pady=5,
                cursor="hand2"
            )
            copy_id_btn.pack(side=tk.RIGHT)
        
        # Область для текста
        text_area = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            font=("DejaVu Sans Mono", 10)
        )
        text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Форматируем данные записи
        text = self.format_record_details(record)
        text_area.insert(tk.END, text)
        text_area.config(state='disabled')
        
        # Кнопки
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X)
        
        copy_all_btn = tk.Button(
            buttons_frame,
            text="📋 Копировать всё",
            command=lambda: self.copy_record_to_clipboard(record)
        )
        copy_all_btn.config(
            background="#3498db",
            foreground="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2"
        )
        copy_all_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        close_btn = tk.Button(
            buttons_frame,
            text="Закрыть",
            command=details_window.destroy
        )
        close_btn.config(
            background="#95a5a6",
            foreground="white",
            font=("Arial", 10),
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2"
        )
        close_btn.pack(side=tk.RIGHT)
    
    def copy_single_id(self, client_id):
        """Копирует один ID клиента в буфер обмена"""
        try:
            # Используем метод copy_to_clipboard
            self.copy_to_clipboard(client_id, f"ID клиента")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать ID: {e}")
    
    def format_record_details(self, record):
        """Форматирует детали записи для отображения"""
        text = f"{'='*80}\n"
        text += "ПОЛНАЯ ИНФОРМАЦИЯ О КЛИЕНТЕ\n"
        text += f"{'='*80}\n\n"
        
        # Группируем поля по категориям
        categories = {
            'Основная информация': ['id', 'client_id', 'create_date', 'update_date'],
            'ФИО': ['last_name', 'first_name', 'patronymic'],
            'Контактная информация': ['email', 'phone', 'mobile_phone', 'address'],
            'Дополнительная информация': ['inn', 'snils', 'passport']
        }
        
        # Добавляем все поля
        for category, fields in categories.items():
            text += f"{category}:\n"
            text += f"{'-'*40}\n"
            
            for field in fields:
                if field in record and record[field] is not None:
                    value = record[field]
                    if hasattr(value, 'strftime'):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        value = str(value)
                    
                    if value.strip():
                        text += f"  {field}: {value}\n"
            
            text += "\n"
        
        # Добавляем остальные поля
        other_fields = [f for f in record.keys() 
                       if f not in sum(categories.values(), [])]
        
        if other_fields:
            text += f"Прочие поля:\n"
            text += f"{'-'*40}\n"
            
            for field in other_fields:
                if record[field] is not None:
                    value = record[field]
                    if hasattr(value, 'strftime'):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        value = str(value)
                    
                    if value.strip():
                        text += f"  {field}: {value}\n"
        
        text += f"\n{'='*80}\n"
        
        return text
    
    def setup_docs_tab(self, parent):
        """Настраивает вкладку проверки документов"""
        frame = ttk.Frame(parent, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        tk.Label(
            frame,
            text="Проверка документов клиента",
            font=("Arial", 14, "bold"),
            foreground="#2c3e50"
        ).pack(pady=(0, 10))
        
        # Описание
        tk.Label(
            frame,
            text="Ищет документы в таблицах: one_load_history, pto_ts_own и других",
            font=("Arial", 10),
            foreground="#7f8c8d",
            wraplength=600
        ).pack(pady=(0, 20))
        
        # Поле ввода ID клиента
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(input_frame, text="ID клиента:", font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 10))
        
        self.client_id_entry = ttk.Entry(
            input_frame,
            textvariable=self.search_client_id_var,
            width=30,
            font=("Arial", 11)
        )
        self.client_id_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Фрейм для кнопок
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Кнопка проверки
        check_btn = tk.Button(
            buttons_frame,
            text="🔍 Проверить документы",
            command=lambda: self.check_documents(self.search_client_id_var.get())
        )
        check_btn.config(
            background="#2ecc71",
            foreground="white",
            font=("Arial", 11, "bold"),
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2"
        )
        check_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Кнопка тестирования (для отладки)
        test_btn = tk.Button(
            buttons_frame,
            text="⚡ Тестовый запрос",
            command=lambda: self.test_document_query(self.search_client_id_var.get())
        )
        test_btn.config(
            background="#e67e22",
            foreground="white",
            font=("Arial", 10),
            relief="flat",
            padx=15,
            pady=6,
            cursor="hand2"
        )
        test_btn.pack(side=tk.LEFT)
        
        # Привязываем Enter к поиску
        self.client_id_entry.bind('<Return>', lambda e: self.check_documents(self.search_client_id_var.get()))
        
        # Область для результатов проверки документов
        self.docs_result_text = scrolledtext.ScrolledText(
            frame,
            wrap=tk.WORD,
            height=10,
            font=("DejaVu Sans Mono", 10)
        )
        self.docs_result_text.config(
            background="#f8f9fa",
            padx=10,
            pady=10
        )
        self.docs_result_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Статус проверки
        self.docs_status_label = tk.Label(
            frame,
            text="Введите ID клиента для проверки документов",
            font=("Arial", 10),
            foreground="#7f8c8d"
        )
        self.docs_status_label.pack()
    
    def test_document_query(self, client_id):
        """Выполняет тестовый запрос для отладки"""
        if not client_id or client_id.strip() == "":
            messagebox.showwarning("Внимание", "Введите ID клиента для теста")
            return
        
        self.status_var.set(f"Тестовый запрос для клиента ID: {client_id}")
        
        threading.Thread(
            target=self._perform_test_query,
            args=(client_id.strip(),),
            daemon=True
        ).start()
    
    def _perform_test_query(self, client_id):
        """Выполняет тестовый запрос в отдельном потоке"""
        try:
            results = self.db_client.test_document_query(client_id)
            
            if results is None:
                self.window.after(0, lambda: messagebox.showerror(
                    "Тест", 
                    "Тестовый запрос не выполнен. Проверьте подключение к БД."
                ))
            elif len(results) == 0:
                self.window.after(0, lambda: messagebox.showinfo(
                    "Тест", 
                    f"Тестовый запрос выполнен. Для клиента {client_id} записей не найдено."
                ))
            else:
                self.window.after(0, lambda: messagebox.showinfo(
                    "Тест", 
                    f"Тестовый запрос успешен! Найдено {len(results)} записей.\n"
                    f"Проверьте логи для детальной информации."
                ))
                
        except Exception as e:
            self.window.after(0, lambda: messagebox.showerror(
                "Ошибка теста", 
                f"Ошибка при выполнении тестового запроса: {e}"
            ))
    
    def setup_docs_tab(self, parent):
        """Настраивает вкладку проверки документов"""
        frame = ttk.Frame(parent, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        tk.Label(
            frame,
            text="Проверка документов клиента",
            font=("Arial", 14, "bold"),
            foreground="#2c3e50"
        ).pack(pady=(0, 10))
        
        # Описание
        tk.Label(
            frame,
            text="Ищет документы в таблицах: one_load_history, pto_ts_own и других",
            font=("Arial", 10),
            foreground="#7f8c8d",
            wraplength=600
        ).pack(pady=(0, 20))
        
        # Поле ввода ID клиента
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(input_frame, text="ID клиента:", font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 10))
        
        self.client_id_entry = ttk.Entry(
            input_frame,
            textvariable=self.search_client_id_var,
            width=30,
            font=("Arial", 11)
        )
        self.client_id_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Фрейм для кнопок
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Кнопка проверки
        check_btn = tk.Button(
            buttons_frame,
            text="🔍 Проверить документы",
            command=lambda: self.check_documents(self.search_client_id_var.get())
        )
        check_btn.config(
            background="#2ecc71",
            foreground="white",
            font=("Arial", 11, "bold"),
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2"
        )
        check_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Кнопка тестирования (для отладки)
        test_btn = tk.Button(
            buttons_frame,
            text="⚡ Тестовый запрос",
            command=lambda: self.test_document_query(self.search_client_id_var.get())
        )
        test_btn.config(
            background="#e67e22",
            foreground="white",
            font=("Arial", 10),
            relief="flat",
            padx=15,
            pady=6,
            cursor="hand2"
        )
        test_btn.pack(side=tk.LEFT)
        
        # Привязываем Enter к поиску
        self.client_id_entry.bind('<Return>', lambda e: self.check_documents(self.search_client_id_var.get()))
        
        # Область для результатов проверки документов
        self.docs_result_text = scrolledtext.ScrolledText(
            frame,
            wrap=tk.WORD,
            height=10,
            font=("DejaVu Sans Mono", 10)
        )
        self.docs_result_text.config(
            background="#f8f9fa",
            padx=10,
            pady=10
        )
        self.docs_result_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Статус проверки
        self.docs_status_label = tk.Label(
            frame,
            text="Введите ID клиента для проверки документов",
            font=("Arial", 10),
            foreground="#7f8c8d"
        )
        self.docs_status_label.pack()
    
    def test_document_query(self, client_id):
        """Выполняет тестовый запрос для отладки"""
        if not client_id or client_id.strip() == "":
            messagebox.showwarning("Внимание", "Введите ID клиента для теста")
            return
        
        self.status_var.set(f"Тестовый запрос для клиента ID: {client_id}")
        
        threading.Thread(
            target=self._perform_test_query,
            args=(client_id.strip(),),
            daemon=True
        ).start()
    
    def _perform_test_query(self, client_id):
        """Выполняет тестовый запрос в отдельном потоке"""
        try:
            results = self.db_client.test_document_query(client_id)
            
            if results is None:
                self.window.after(0, lambda: messagebox.showerror(
                    "Тест", 
                    "Тестовый запрос не выполнен. Проверьте подключение к БД."
                ))
            elif len(results) == 0:
                self.window.after(0, lambda: messagebox.showinfo(
                    "Тест", 
                    f"Тестовый запрос выполнен. Для клиента {client_id} записей не найдено."
                ))
            else:
                self.window.after(0, lambda: messagebox.showinfo(
                    "Тест", 
                    f"Тестовый запрос успешен! Найдено {len(results)} записей.\n"
                    f"Проверьте логи для детальной информации."
                ))
                
        except Exception as e:
            self.window.after(0, lambda: messagebox.showerror(
                "Ошибка теста", 
                f"Ошибка при выполнении тестового запроса: {e}"
            ))
    
    def copy_record_to_clipboard(self, record):
        """Копирует запись в буфер обмена"""
        try:
            text = self.format_record_details(record)
            # Используем метод copy_to_clipboard
            self.copy_to_clipboard(text, "Запись")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать: {e}")
    
    def format_results_for_export(self, is_csv=False):
        """Форматирует результаты для экспорта в файл"""
        if not self.current_results:
            return ""
        
        if is_csv:
            # CSV формат
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
            
            # Заголовок
            if self.current_results:
                headers = list(self.current_results[0].keys())
                writer.writerow(headers)
            
            # Данные
            for record in self.current_results:
                row = []
                for key in headers:
                    value = record.get(key, '')
                    if value is None:
                        value = ''
                    elif hasattr(value, 'strftime'):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        value = str(value)
                    row.append(value)
                writer.writerow(row)
            
            return output.getvalue()
        else:
            # Текстовый формат
            text = f"Экспорт данных из БД {self.db_client.current_database}\n"
            text += f"Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            text += f"Количество записей: {len(self.current_results)}\n"
            text += "="*80 + "\n\n"
            
            for i, record in enumerate(self.current_results, 1):
                text += f"Запись #{i}:\n"
                text += "-"*40 + "\n"
                
                for key, value in record.items():
                    if value is not None:
                        if hasattr(value, 'strftime'):
                            value = value.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            value = str(value)
                        text += f"{key}: {value}\n"
                
                text += "\n"
            
            return text
        
    