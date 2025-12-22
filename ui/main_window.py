# ui/main_window.py - Главное окно приложения
import os
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from datetime import datetime

from config import Config
from proxy_manager import ProxyManager
from mail_client import MailClient
from database_client import DatabaseClient
from utils.logger import Logger
from .db_work_window import DatabaseWorkWindow

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title(Config.APP_TITLE)
        self.root.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")
        
        # Центрируем окно
        self.center_window()
        
        # Инициализируем компоненты
        self.logger = Logger()
        self.proxy_manager = ProxyManager()
        self.mail_client = MailClient(self.logger)
        self.db_client = DatabaseClient(self.logger)
        
        # Переменные состояния
        self.proxy_status = False
        self.mail_status = False
        self.db_status = False
        self.is_fetching = False
        
        # Настройка интерфейса
        self.setup_ui()
        
        # Авто-тест подключения
        self.root.after(1000, self.auto_test_connection)
    
    def center_window(self):
        """Центрирует окно на экране"""
        self.root.update_idletasks()
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = (screen_width - Config.WINDOW_WIDTH) // 2
        y = (screen_height - Config.WINDOW_HEIGHT) // 2
        
        self.root.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}+{x}+{y}")
    
    def setup_ui(self):
        """Настраивает пользовательский интерфейс"""
        # Основной контейнер
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Левая панель - управление
        left_panel = ttk.Frame(main_container)
        main_container.add(left_panel, weight=1)
        
        # Правая панель - информация
        right_panel = ttk.Frame(main_container)
        main_container.add(right_panel, weight=3)
        
        # ===== ЛЕВАЯ ПАНЕЛЬ =====
        self.setup_left_panel(left_panel)
        
        # ===== ПРАВАЯ ПАНЕЛЬ =====
        self.setup_right_panel(right_panel)
    
    def setup_left_panel(self, parent):
        """Настраивает левую панель управления"""
        # Панель информации о сервере
        server_frame = ttk.LabelFrame(parent, text="Информация о сервере", padding="10")
        server_frame.pack(fill=tk.X, padx=5, pady=(0, 10))
        
        info_text = f"""
Сервер: {Config.MAIL_SERVER}
Пользователь: {Config.USERNAME}
Прокси: {Config.PROXY_HOST}:{Config.PROXY_PORT}
SQL Server: {Config.SQL_SERVER}:{Config.SQL_PORT}
База данных: {Config.SQL_DATABASE}
"""
        
        info_label = tk.Label(server_frame, text=info_text, justify=tk.LEFT, anchor=tk.W)
        info_label.pack(fill=tk.X)
        
        # Панель параметров поиска
        search_frame = ttk.LabelFrame(parent, text="Параметры поиска", padding="10")
        search_frame.pack(fill=tk.X, padx=5, pady=(0, 10))
        
        # Период поиска
        ttk.Label(search_frame, text="Период поиска (дней):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.days_var = tk.StringVar(value="30")
        days_combo = ttk.Combobox(search_frame, textvariable=self.days_var, 
                                 values=["1", "7", "30", "90", "180"], width=15)
        days_combo.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)
        
        # Папка для поиска
        ttk.Label(search_frame, text="Папка:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.folder_var = tk.StringVar(value="INBOX")
        folder_combo = ttk.Combobox(search_frame, textvariable=self.folder_var, 
                                   values=["INBOX", "Sent", "Drafts", "Trash"], width=15)
        folder_combo.grid(row=1, column=1, pady=5, padx=5, sticky=tk.W)
        
        # Максимум писем
        ttk.Label(search_frame, text="Макс. писем:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.limit_var = tk.StringVar(value="50")
        limit_combo = ttk.Combobox(search_frame, textvariable=self.limit_var, 
                                  values=["10", "25", "50", "100", "500"], width=15)
        limit_combo.grid(row=2, column=1, pady=5, padx=5, sticky=tk.W)
        
        # Отправитель
        ttk.Label(search_frame, text="Отправитель:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.sender_var = tk.StringVar(value=Config.TARGET_SENDER)
        sender_entry = ttk.Entry(search_frame, textvariable=self.sender_var, width=15)
        sender_entry.grid(row=3, column=1, pady=5, padx=5, sticky=tk.W)
        
        # Панель кнопок
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill=tk.X, padx=5, pady=(10, 0))
        
        button_configs = [
            ("Тест подключений", self.test_all_connections, "#2196F3"),
            ("Получить письма", self.start_fetch_emails, "#4CAF50"),
            ("Работа в БД", self.open_db_work_window, "#FF9800"),
            ("Отчеты", self.show_reports, "#9C27B0"),
            ("Настройки", self.open_settings, "#607D8B"),
            ("Очистить логи", self.clear_logs, "#f44336"),
            ("Системная информация", self.show_sys_info, "#009688"),
            ("Выход", self.root.quit, "#795548")
        ]
        
        for text, command, color in button_configs:
            btn = tk.Button(buttons_frame, text=text, command=command)
            btn.config(
                background=color,
                foreground="white",
                font=("Arial", 10, "bold"),
                relief="flat",
                padx=15,
                pady=10,
                width=20,
                cursor="hand2"
            )
            btn.pack(pady=3)
            
            # Эффекты при наведении
            btn.bind("<Enter>", lambda e, b=btn: b.config(background="#555555"))
            btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(background=c))
    
    def setup_right_panel(self, parent):
        """Настраивает правую панель информации"""
        # Панель статусов
        status_frame = tk.Frame(parent, bg="#f0f0f0", height=50)
        status_frame.pack(fill=tk.X, padx=5, pady=(0, 10))
        status_frame.pack_propagate(False)
        
        self.proxy_status_var = tk.StringVar(value="Прокси: Проверка...")
        self.mail_status_var = tk.StringVar(value="Почта: Проверка...")
        self.db_status_var = tk.StringVar(value="БД: Проверка...")
        
        status_labels = [
            (self.proxy_status_var, "#2196F3"),
            (self.mail_status_var, "#4CAF50"),
            (self.db_status_var, "#FF9800"),
        ]
        
        for var, color in status_labels:
            lbl = tk.Label(status_frame, textvariable=var)
            lbl.config(
                background=color,
                foreground="white",
                font=("Arial", 10, "bold"),
                padx=15,
                pady=8,
                relief="ridge",
                bd=1
            )
            lbl.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Вкладки
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 10))
        
        # Вкладка: Письма
        emails_tab = ttk.Frame(notebook)
        notebook.add(emails_tab, text="📧 Письма")
        
        # Панель инструментов для писем
        emails_toolbar = tk.Frame(emails_tab, bg="#e0e0e0", height=40)
        emails_toolbar.pack(fill=tk.X)
        emails_toolbar.pack_propagate(False)
        
        toolbar_buttons = [
            ("🔄 Обновить", self.start_fetch_emails, "#4CAF50"),
            ("🗑️ Очистить", lambda: self.emails_area.delete(1.0, tk.END), "#f44336"),
            ("📋 Копировать", self.copy_emails, "#2196F3"),
            ("💾 Экспорт", self.export_emails, "#FF9800")
        ]
        
        for text, command, color in toolbar_buttons:
            btn = tk.Button(emails_toolbar, text=text, command=command)
            btn.config(
                background=color,
                foreground="white",
                relief="flat",
                padx=10,
                pady=5,
                cursor="hand2"
            )
            btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        # Область для отображения писем
        self.emails_area = scrolledtext.ScrolledText(
            emails_tab,
            wrap=tk.WORD,
            font=("DejaVu Sans Mono", 10)
        )
        self.emails_area.config(
            background="#f8f9fa",
            padx=10,
            pady=10
        )
        self.emails_area.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка: Логи
        logs_tab = ttk.Frame(notebook)
        notebook.add(logs_tab, text="📝 Логи")
        
        self.logs_area = scrolledtext.ScrolledText(
            logs_tab,
            wrap=tk.WORD,
            font=("DejaVu Sans Mono", 9)
        )
        self.logs_area.config(
            background="#1e1e1e",
            foreground="#00ff00",
            padx=10,
            pady=10
        )
        self.logs_area.pack(fill=tk.BOTH, expand=True)
        
        # Устанавливаем виджет логов в логгер
        self.logger.set_text_widget(self.logs_area)
        
        # Прогресс бар
        progress_frame = tk.Frame(parent)
        progress_frame.pack(fill=tk.X, padx=5, pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.progress_label = tk.Label(progress_frame, text="0%", font=("Arial", 10))
        self.progress_label.pack(side=tk.RIGHT)
        
        # Статусная строка
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = tk.Label(
            parent,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.config(
            background="#e8e8e8",
            padx=15,
            pady=8,
            font=("Arial", 10)
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def auto_test_connection(self):
        """Автоматический тест подключений при запуске"""
        self.logger.log("=" * 60)
        self.logger.log("АВТОМАТИЧЕСКИЙ ТЕСТ ПОДКЛЮЧЕНИЙ", "INFO")
        
        # Тест прокси
        self.proxy_status = self.proxy_manager.setup_mail_proxy()
        if self.proxy_status:
            self.proxy_status_var.set("Прокси: Настроен")
            self.logger.log("Прокси настроен", "SUCCESS")
        else:
            self.proxy_status_var.set("Прокси: Ошибка")
            self.logger.log("Ошибка настройки прокси", "ERROR")
        
        # Тест БД
        threading.Thread(target=self.test_db_background, daemon=True).start()
        
        # Тест почты
        threading.Thread(target=self.test_mail_background, daemon=True).start()
    
    def test_db_background(self):
        """Фоновый тест подключения к БД"""
        self.db_status = self.db_client.test_connection()
        if self.db_status:
            self.db_status_var.set(f"БД: {self.db_client.current_database}")
            self.logger.log(f"База данных '{self.db_client.current_database}' доступна", "SUCCESS")
        else:
            self.db_status_var.set("БД: Недоступна")
            self.logger.log("База данных недоступна", "ERROR")
    
    def test_mail_background(self):
        """Фоновый тест подключения к почте"""
        self.mail_status = self.mail_client.test_connection()
        if self.mail_status:
            self.mail_status_var.set("Почта: Доступна")
            self.logger.log("Почта подключена", "SUCCESS")
        else:
            self.mail_status_var.set("Почта: Ошибка")
            self.logger.log("Почта недоступна", "ERROR")
    
    def test_all_connections(self):
        """Тестирует все подключения"""
        self.logger.log("=" * 60)
        self.logger.log("ПОЛНЫЙ ТЕСТ ПОДКЛЮЧЕНИЙ", "INFO")
        
        self.status_var.set("Тестирование подключений...")
        
        # Сбрасываем статусы
        self.proxy_status_var.set("Прокси: Тестируется...")
        self.mail_status_var.set("Почта: Тестируется...")
        self.db_status_var.set("БД: Тестируется...")
        
        # Тест прокси
        self.proxy_status = self.proxy_manager.test_proxy_connection()
        self.proxy_status_var.set("Прокси: Работает" if self.proxy_status else "Прокси: Ошибка")
        
        # Тест БД в отдельном потоке
        db_thread = threading.Thread(target=self.test_db_background, daemon=True)
        db_thread.start()
        
        # Тест почты в отдельном потоке
        mail_thread = threading.Thread(target=self.test_mail_background, daemon=True)
        mail_thread.start()
        
        # Ждем завершения потоков
        db_thread.join(timeout=30)
        mail_thread.join(timeout=30)
        
        self.logger.log("Тестирование завершено", "INFO")
        self.status_var.set("Готов к работе")
    
    def start_fetch_emails(self):
        """Запускает получение писем"""
        if self.is_fetching:
            self.logger.log("Получение писем уже выполняется", "WARNING")
            return
        
        self.is_fetching = True
        self.status_var.set("Начинаю получение писем...")
        
        threading.Thread(target=self.fetch_emails_thread, daemon=True).start()
    
    def fetch_emails_thread(self):
        """Поток для получения писем"""
        try:
            # Очищаем область писем
            self.emails_area.delete(1.0, tk.END)
            self.progress_var.set(0)
            self.progress_label.config(text="0%")
            
            # Получаем параметры
            days = int(self.days_var.get())
            folder = self.folder_var.get()
            limit = int(self.limit_var.get())
            sender = self.sender_var.get().strip() or Config.TARGET_SENDER
            
            # Получаем письма
            self.status_var.set("Поиск писем...")
            emails = self.mail_client.search_emails(
                folder=folder,
                days=days,
                sender=sender,
                limit=limit
            )
            
            # Обновляем прогресс
            self.progress_var.set(50)
            self.progress_label.config(text="50%")
            self.status_var.set("Обработка результатов...")
            
            # Отображаем письма
            self.display_emails(emails)
            
            # Завершаем прогресс
            self.progress_var.set(100)
            self.progress_label.config(text="100%")
            self.status_var.set(f"Готово. Найдено писем: {len(emails)}")
            
        except Exception as e:
            self.logger.log(f"Ошибка получения писем: {e}", "ERROR")
            self.status_var.set("Ошибка получения писем")
        finally:
            self.is_fetching = False
    
    def display_emails(self, emails):
        """Отображает письма в интерфейсе"""
        if not emails:
            self.emails_area.insert(tk.END, "Писем не найдено\n")
            return
        
        for i, email_data in enumerate(emails, 1):
            self.emails_area.insert(tk.END, f"\n{'='*80}\n")
            self.emails_area.insert(tk.END, f"ПИСЬМО #{i}\n\n")
            
            # Основная информация
            self.emails_area.insert(tk.END, f"Тема: {email_data['subject']}\n")
            self.emails_area.insert(tk.END, f"Дата: {email_data['date_received'].strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.emails_area.insert(tk.END, f"От: {email_data['sender_name']}\n")
            self.emails_area.insert(tk.END, f"Email: {email_data['sender_email']}\n")
            
            if email_data['has_attachment']:
                self.emails_area.insert(tk.END, f"📎 Вложений: {email_data['attachment_count']}\n")
            
            # Показываем первые 2 письма подробно
            if i <= 2 and email_data['body_text']:
                preview = email_data['body_text']
                if len(preview) > 300:
                    preview = preview[:300] + "..."
                
                self.emails_area.insert(tk.END, f"\nСодержание:\n{preview}\n")
            
            # Обновляем прогресс
            progress = (i / len(emails)) * 50 + 50  # 50-100%
            self.progress_var.set(progress)
            self.progress_label.config(text=f"{int(progress)}%")
            
            # Обновляем интерфейс
            if i % 5 == 0:
                self.root.update_idletasks()
        
        # Итоги
        self.emails_area.insert(tk.END, f"\n{'═'*80}\n")
        self.emails_area.insert(tk.END, f"ИТОГИ\n")
        self.emails_area.insert(tk.END, f"{'═'*80}\n")
        self.emails_area.insert(tk.END, f"• Обработано писем: {len(emails)}\n")
        self.emails_area.insert(tk.END, f"• Отправитель: {self.sender_var.get()}\n")
        self.emails_area.insert(tk.END, f"• Период: последние {self.days_var.get()} дней\n")
        self.emails_area.insert(tk.END, f"• Папка: {self.folder_var.get()}\n")
        
        # Прокручиваем в начало
        self.emails_area.see(1.0)
    
    def open_db_work_window(self):
        """Открывает окно для работы с БД"""
        try:
            db_window = DatabaseWorkWindow(self.root, self.db_client, self.logger)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть окно работы с БД:\n{e}")
    
    def show_reports(self):
        """Показывает окно отчетов"""
        self.logger.log("Функция отчетов в разработке", "INFO")
        messagebox.showinfo("Отчеты", "Функция отчетов находится в разработке")
    
    def open_settings(self):
        """Открывает окно настроек"""
        self.logger.log("Функция настроек в разработке", "INFO")
        messagebox.showinfo("Настройки", "Функция настроек находится в разработке")
    
    def clear_logs(self):
        """Очищает логи"""
        self.logger.clear()
        self.status_var.set("Логи очищены")
    
    def show_sys_info(self):
        """Показывает системную информацию"""
        import sys
        import platform
        
        info = f"""
{'='*80}
СИСТЕМНАЯ ИНФОРМАЦИЯ
{'='*80}

СИСТЕМА:
• ОС: {platform.system()} {platform.release()}
• Процессор: {platform.processor()}
• Python: {sys.version}

ДИРЕКТОРИИ:
• Текущая: {os.getcwd()}
• Исполняемый файл: {sys.executable}

ВРЕМЯ:
• Текущее: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Часовой пояс: {time.tzname[0]}

{'='*80}
"""
        
        self.emails_area.delete(1.0, tk.END)
        self.emails_area.insert(tk.END, info)
        self.logger.log("Показана системная информация", "INFO")
        self.status_var.set("Системная информация отображена")
    
    def copy_emails(self):
        """Копирует содержимое писем в буфер обмена"""
        try:
            text = self.emails_area.get(1.0, tk.END).strip()
            if text:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.logger.log("Письма скопированы в буфер обмена", "SUCCESS")
                self.status_var.set("Письма скопированы")
            else:
                messagebox.showinfo("Информация", "Нет данных для копирования")
        except Exception as e:
            self.logger.log(f"Ошибка копирования: {e}", "ERROR")
            messagebox.showerror("Ошибка", f"Не удалось скопировать: {e}")
    
    def export_emails(self):
        """Экспортирует письма в файл"""
        try:
            text = self.emails_area.get(1.0, tk.END).strip()
            if not text:
                messagebox.showinfo("Информация", "Нет данных для экспорта")
                return
            
            # Создаем файл в домашней директории
            home_dir = os.path.expanduser("~")
            filename = os.path.join(home_dir, f"oblgaz_emails_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(text)
            
            self.logger.log(f"Письма экспортированы в: {filename}", "SUCCESS")
            self.status_var.set(f"Экспорт завершен: {os.path.basename(filename)}")
            messagebox.showinfo("Экспорт", f"Данные экспортированы в файл:\n{filename}")
            
        except Exception as e:
            self.logger.log(f"Ошибка экспорта: {e}", "ERROR")
            messagebox.showerror("Ошибка", f"Не удалось экспортировать: {e}")