#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import imaplib
import smtplib
import email
import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import threading
from datetime import datetime, timedelta
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pymssql
import socks
import socket
import ssl
import time
import re

# ============================================
# КОНФИГУРАЦИЯ ПОЧТОВОГО СЕРВЕРА OBLGAZ
# ============================================

# Параметры сервера (из Thunderbird)
MAIL_SERVER = 'mail.oblgaz.nnov.ru'
SMTP_PORT = 587
IMAP_PORT = 993  # Обычный порт для IMAP с SSL
USERNAME = 'kuzminiv@oblgaz.nnov.ru'
PASSWORD = 'sup800'  # Пароль от почты

# Параметры прокси
PROXY_HOST = '192.168.1.2'
PROXY_PORT = 8080
PROXY_USER = 'kuzminiv'
PROXY_PASS = '12345678Q!'

# Параметры SQL Server
SQL_SERVER = '192.168.1.224'
SQL_PORT = 1433
SQL_DATABASE = 'DOG'  # Изменено на DOG
SQL_USERNAME = 'kuzmin'
SQL_PASSWORD = '76543210'

# Целевой отправитель для поиска
TARGET_SENDER = 'support_lk@oblgaz.nnov.ru'

# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЧТОЙ OBLGAZ
# ============================================

def check_linux_dependencies():
    """Проверяем установку необходимых пакетов в Linux"""
    missing_packages = []
    
    try:
        import pymssql
    except ImportError:
        missing_packages.append("pymssql")
    
    try:
        import socks
    except ImportError:
        missing_packages.append("pysocks")
    
    try:
        import tkinter
    except ImportError:
        missing_packages.append("python3-tk")
    
    if missing_packages:
        print(f"Не хватает пакетов: {', '.join(missing_packages)}")
        
        # Для RedOS (основана на CentOS/RHEL)
        print("\nУстановка для RedOS/CentOS/RHEL:")
        print("  sudo yum install python3-devel gcc freetds-devel")
        print(f"  sudo pip3 install {' '.join(missing_packages)}")
        
        return False
    
    return True

def setup_mail_proxy():
    """Настраиваем прокси для почтовых соединений"""
    try:
        # Сохраняем оригинальные функции
        original_socket = socket.socket
        original_create_connection = socket.create_connection
        
        def create_proxy_socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, fileno=None):
            """Создает сокет с настройкой прокси"""
            if fileno is None:
                sock = socks.socksocket(family=family, type=type, proto=proto)
                sock.set_proxy(
                    socks.SOCKS5,
                    PROXY_HOST,
                    PROXY_PORT,
                    username=PROXY_USER,
                    password=PROXY_PASS,
                    rdns=True
                )
                return sock
            return original_socket(family, type, proto, fileno)
        
        # Патчим socket для использования прокси
        socket.socket = create_proxy_socket
        
        def patched_create_connection(address, timeout=None, source_address=None):
            """Патчим create_connection для работы с прокси"""
            host, port = address
            
            # Принудительно используем IPv4 для обхода проблем
            addrinfo = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
            
            for family, socktype, proto, canonname, sockaddr in addrinfo:
                sock = None
                try:
                    sock = create_proxy_socket(family, socktype, proto)
                    
                    if timeout is not None:
                        sock.settimeout(timeout)
                    
                    if source_address:
                        sock.bind(source_address)
                    
                    sock.connect(sockaddr)
                    return sock
                    
                except Exception:
                    if sock is not None:
                        sock.close()
                    continue
            
            raise OSError(f"Не удалось подключиться к {host}:{port}")
        
        socket.create_connection = patched_create_connection
        
        # Настраиваем переменные окружения
        os.environ['HTTP_PROXY'] = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"
        os.environ['HTTPS_PROXY'] = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"
        os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
        
        print(f"Прокси настроен: {PROXY_HOST}:{PROXY_PORT}")
        print(f"Пользователь прокси: {PROXY_USER}")
        
        return True
        
    except Exception as e:
        print(f"Ошибка настройки прокси: {e}")
        return False

def test_mail_connection():
    """Тестирует подключение к почтовому серверу"""
    print(f"\nТестирование подключения к {MAIL_SERVER}...")
    
    # Тест SMTP (порт 587 с STARTTLS)
    try:
        print(f"  SMTP (порт {SMTP_PORT})...")
        
        # Создаем SMTP соединение через прокси
        smtp_conn = smtplib.SMTP(
            host=MAIL_SERVER,
            port=SMTP_PORT,
            timeout=30
        )
        
        # Приветствие
        smtp_conn.ehlo()
        
        # STARTTLS шифрование
        smtp_conn.starttls()
        smtp_conn.ehlo()
        
        # Аутентификация
        smtp_conn.login(USERNAME, PASSWORD)
        
        print(f"  SMTP подключение успешно")
        smtp_conn.quit()
        
    except Exception as e:
        print(f"  SMTP ошибка: {e}")
        return False
    
    # Тест IMAP (порт 993 с SSL)
    try:
        print(f"  IMAP (порт {IMAP_PORT})...")
        
        # Создаем SSL контекст
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Подключаемся к IMAP с SSL
        imap_conn = imaplib.IMAP4_SSL(
            host=MAIL_SERVER,
            port=IMAP_PORT,
            ssl_context=ssl_context
        )
        
        # Устанавливаем таймаут для сокета
        imap_conn.sock.settimeout(30.0)
        
        # Логинимся
        imap_conn.login(USERNAME, PASSWORD)
        
        print(f"  IMAP подключение успешно")
        
        # Проверяем доступные папки
        status, folders = imap_conn.list()
        if status == 'OK':
            print(f"  Найдено папок: {len(folders)}")
        
        imap_conn.logout()
        
    except Exception as e:
        print(f"  IMAP ошибка: {e}")
        
        # Пробуем альтернативный порт 143 с STARTTLS
        try:
            print(f"  Пробуем IMAP порт 143...")
            imap_conn = imaplib.IMAP4(MAIL_SERVER, 143)
            imap_conn.sock.settimeout(30.0)
            imap_conn.starttls()
            imap_conn.login(USERNAME, PASSWORD)
            print(f"  IMAP (порт 143) успешно")
            imap_conn.logout()
        except Exception as e2:
            print(f"  IMAP порт 143 также не работает: {e2}")
            return False
    
    print(f"\nВсе подключения к почте работают!")
    return True

def get_imap_connection_oblgaz():
    """Создает подключение к IMAP серверу oblgaz"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"Попытка IMAP подключения {attempt + 1}/{max_retries}...")
            
            # Создаем SSL контекст
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # ИСПРАВЛЕНИЕ: Создаем подключение БЕЗ параметра timeout в конструкторе
            mail = imaplib.IMAP4_SSL(
                host=MAIL_SERVER,
                port=IMAP_PORT,
                ssl_context=ssl_context  # Убрали 'timeout=45'
            )
            
            # ИСПРАВЛЕНИЕ: Устанавливаем таймаут через sock.settimeout()
            mail.sock.settimeout(45.0)
            
            # Логинимся
            mail.login(USERNAME, PASSWORD)
            
            print(f"Успешное подключение к {MAIL_SERVER}:{IMAP_PORT}")
            return mail
            
        except socket.timeout:
            print(f"Таймаут подключения (попытка {attempt + 1})")
            if attempt < max_retries - 1:
                time.sleep(3)
        except ssl.SSLError as e:
            print(f"SSL ошибка: {e}")
            
            # Пробуем без SSL проверки
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                mail = imaplib.IMAP4_SSL(
                    host=MAIL_SERVER,
                    port=IMAP_PORT,
                    ssl_context=ssl_context
                )
                mail.sock.settimeout(45.0)
                mail.login(USERNAME, PASSWORD)
                print(f"Подключение без проверки SSL успешно")
                return mail
            except:
                if attempt < max_retries - 1:
                    time.sleep(3)
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
    
    return None

def get_sql_connection(database=None):
    """Подключается к SQL Server"""
    try:
        conn = pymssql.connect(
            server=SQL_SERVER,
            port=SQL_PORT,
            user=SQL_USERNAME,
            password=SQL_PASSWORD,
            database=database or SQL_DATABASE,
            charset='UTF-8',
            login_timeout=15
        )
        return conn
    except pymssql.OperationalError as e:
        if "database" in str(e).lower():
            print(f"Ошибка: База данных '{database or SQL_DATABASE}' не найдена")
            return None
        else:
            print(f"Ошибка подключения к SQL Server: {e}")
            return None
    except Exception as e:
        print(f"Ошибка подключения к SQL Server: {e}")
        return None

def get_available_databases():
    """Получаем список доступных баз данных"""
    conn = get_sql_connection('master')
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT name 
        FROM sys.databases 
        WHERE state = 0 AND name NOT IN ('master', 'model', 'msdb', 'tempdb')
        ORDER BY name
        """)
        
        databases = [row[0] for row in cursor.fetchall()]
        return databases
        
    except Exception as e:
        print(f"Ошибка получения списка БД: {e}")
        return []
    finally:
        conn.close()

def check_dog_database():
    """Проверяет доступность базы данных DOG"""
    print("Проверка базы данных DOG...")
    
    # Сначала пробуем подключиться к DOG напрямую
    conn = get_sql_connection('DOG')
    if conn:
        try:
            cursor = conn.cursor()
            # Проверяем наличие нужной таблицы
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'srv_client_fl'
            """)
            
            if cursor.fetchone():
                print("✓ База данных DOG доступна и содержит таблицу srv_client_fl")
                conn.close()
                return True
            else:
                print("× База DOG доступна, но не содержит таблицу srv_client_fl")
                conn.close()
                return False
                
        except Exception as e:
            print(f"Ошибка проверки таблиц в DOG: {e}")
            conn.close()
            return False
    
    # Если DOG не доступна, ищем альтернативные базы
    print("База DOG недоступна, поиск альтернативных баз...")
    databases = get_available_databases()
    
    if not databases:
        print("Не удалось получить список баз данных")
        return False
    
    for db_name in databases:
        print(f"Проверяем базу данных: {db_name}...")
        conn = get_sql_connection(db_name)
        if not conn:
            continue
            
        try:
            cursor = conn.cursor()
            # Проверка наличия таблицы srv_client_fl
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'srv_client_fl'
            """)
            
            if cursor.fetchone():
                print(f"✓ Найдена подходящая БД: {db_name}")
                conn.close()
                # Обновляем глобальную переменную с найденной БД
                global SQL_DATABASE
                SQL_DATABASE = db_name
                return True
                
        except Exception as e:
            print(f"  Ошибка проверки БД {db_name}: {e}")
        finally:
            conn.close()
    
    print("Не найдена БД с таблицей srv_client_fl")
    return False

def parse_email_date(date_str):
    """Парсит дату из email заголовка"""
    if not date_str:
        return datetime.now()
    
    try:
        # Убираем временную зону если есть
        date_str = date_str.split('(')[0].strip()
        
        # Пробуем разные форматы дат
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S %Z',
            '%d %b %Y %H:%M:%S %z',
            '%Y-%m-%d %H:%M:%S',
            '%d.%m.%Y %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        # Если ни один формат не подошел
        return datetime.now()
        
    except:
        return datetime.now()

def search_client_by_email(email_address):
    """Ищет клиента в базе по email"""
    conn = get_sql_connection()
    if not conn:
        print("Не удалось подключиться к базе данных")
        return None
    
    try:
        cursor = conn.cursor(as_dict=True)
        
        # Проверяем наличие таблицы
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'srv_client_fl'
        """)
        
        if not cursor.fetchone():
            print("Таблица srv_client_fl не найдена в базе")
            return None
        
        # Выполняем SQL запрос для поиска по email
        query = """
        SELECT *
        FROM srv_client_fl
        WHERE email = %s
        """
        
        cursor.execute(query, (email_address,))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return results
        
    except Exception as e:
        print(f"Ошибка поиска клиента: {e}")
        return None

# ============================================
# КЛАСС ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ
# ============================================

class DatabaseWorkWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Работа в БД")
        self.window.geometry("900x700")
        self.window.resizable(True, True)
        
        # Переменные
        self.search_email_var = tk.StringVar()
        
        # Настройка интерфейса
        self.setup_ui()
        
    def setup_ui(self):
        """Настраивает пользовательский интерфейс"""
        # Основной фрейм
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Заголовок
        header_label = tk.Label(
            main_frame,
            text="Поиск клиентов по email",
            font=("Arial", 16, "bold")
        )
        header_label.config(foreground="#2c3e50")
        header_label.pack(pady=(0, 20))
        
        # Фрейм поиска
        search_frame = ttk.LabelFrame(main_frame, text="Параметры поиска", padding="15")
        search_frame.pack(fill="x", pady=(0, 20))
        
        # Метка и поле для email
        email_label = ttk.Label(search_frame, text="Email клиента:", font=("Arial", 11))
        email_label.pack(side="left", padx=(0, 10))
        
        self.email_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_email_var,
            width=50,
            font=("Arial", 11)
        )
        self.email_entry.pack(side="left", padx=(0, 10))
        
        # Кнопка поиска
        self.search_button = tk.Button(
            search_frame,
            text="Найти",
            command=self.search_client
        )
        self.search_button.config(
            background="#3498db",
            foreground="white",
            font=("Arial", 11, "bold"),
            relief="flat",
            padx=20,
            pady=8
        )
        self.search_button.pack(side="left")
        
        # Привязываем Enter к поиску
        self.email_entry.bind('<Return>', lambda e: self.search_client())
        
        # Фокус на поле ввода при открытии окна
        self.window.after(100, lambda: self.email_entry.focus_set())
        
        # Фрейм для результатов
        results_frame = ttk.LabelFrame(main_frame, text="Результаты поиска", padding="10")
        results_frame.pack(fill="both", expand=True)
        
        # Текстовое поле для результатов
        self.results_text = scrolledtext.ScrolledText(
            results_frame,
            wrap=tk.WORD,
            font=("DejaVu Sans Mono", 10),
            background="#f8f9fa",
            padx=10,
            pady=10
        )
        self.results_text.pack(fill="both", expand=True)
        
        # Панель статуса
        self.status_var = tk.StringVar(value="Готов к поиску")
        status_bar = tk.Label(
            main_frame,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w"
        )
        status_bar.config(
            background="#e8e8e8",
            padx=15,
            pady=8,
            font=("Arial", 10)
        )
        status_bar.pack(side="bottom", fill="x", pady=(10, 0))
        
        # Фрейм кнопок
        buttons_frame = tk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=(10, 0))
        
        # Кнопка очистки
        clear_btn = tk.Button(
            buttons_frame,
            text="Очистить результаты",
            command=self.clear_results
        )
        clear_btn.config(
            background="#e74c3c",
            foreground="white",
            font=("Arial", 10),
            relief="flat",
            padx=15,
            pady=5
        )
        clear_btn.pack(side="left", padx=(0, 10))
        
        # Кнопка копирования
        copy_btn = tk.Button(
            buttons_frame,
            text="Копировать результаты",
            command=self.copy_results
        )
        copy_btn.config(
            background="#2ecc71",
            foreground="white",
            font=("Arial", 10),
            relief="flat",
            padx=15,
            pady=5
        )
        copy_btn.pack(side="left")
        
        # Кнопка экспорта
        export_btn = tk.Button(
            buttons_frame,
            text="Экспорт в файл",
            command=self.export_results
        )
        export_btn.config(
            background="#9b59b6",
            foreground="white",
            font=("Arial", 10),
            relief="flat",
            padx=15,
            pady=5
        )
        export_btn.pack(side="right")
        
        # Добавляем подсказку в поле ввода
        self.add_placeholder()
        
    def add_placeholder(self):
        """Добавляет подсказку в поле ввода email"""
        placeholder_text = "Введите email для поиска..."
        
        def on_entry_click(event):
            """Обработчик клика по полю ввода"""
            if self.email_entry.get() == placeholder_text:
                self.email_entry.delete(0, tk.END)
                # Черный цвет текста
                self.email_entry.config(foreground="#000000")
        
        def on_focusout(event):
            """Обработчик потери фокуса"""
            if self.email_entry.get() == "":
                self.email_entry.insert(0, placeholder_text)
                # Серый цвет текста
                self.email_entry.config(foreground="#999999")
        
        # Устанавливаем подсказку
        self.email_entry.insert(0, placeholder_text)
        self.email_entry.config(foreground="#999999")
        
        # Привязываем обработчики событий
        self.email_entry.bind('<FocusIn>', on_entry_click)
        self.email_entry.bind('<FocusOut>', on_focusout)
        
    def search_client(self):
        """Выполняет поиск клиента по email"""
        email_address = self.search_email_var.get().strip()
        
        # Проверяем, не является ли введенное значение подсказкой
        if email_address == "Введите email для поиска...":
            messagebox.showwarning("Внимание", "Введите email для поиска")
            return
        
        if not email_address:
            messagebox.showwarning("Внимание", "Введите email для поиска")
            return
        
        # Очищаем предыдущие результаты
        self.results_text.delete(1.0, tk.END)
        self.status_var.set(f"Поиск клиента по email: {email_address}")
        
        # Добавляем информацию о запросе
        self.results_text.insert(tk.END, f"{'='*80}\n")
        self.results_text.insert(tk.END, f"ПОИСК КЛИЕНТА ПО EMAIL\n")
        self.results_text.insert(tk.END, f"{'='*80}\n\n")
        self.results_text.insert(tk.END, f"Email для поиска: {email_address}\n")
        self.results_text.insert(tk.END, f"Время запроса: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.results_text.insert(tk.END, f"База данных: {SQL_DATABASE}.dbo.srv_client_fl\n\n")
        
        # Выполняем запрос в отдельном потоке
        threading.Thread(target=self._perform_search, args=(email_address,), daemon=True).start()
    
    def _perform_search(self, email_address):
        """Выполняет поиск в отдельном потоке"""
        try:
            self.status_var.set(f"Выполнение запроса...")
            
            # Выполняем SQL запрос
            results = search_client_by_email(email_address)
            
            # Обновляем UI в главном потоке
            self.window.after(0, self._display_results, results, email_address)
            
        except Exception as e:
            self.window.after(0, self._show_error, str(e))
    
    def _display_results(self, results, email_address):
        """Отображает результаты поиска"""
        if results is None:
            self.results_text.insert(tk.END, f"{'='*80}\n")
            self.results_text.insert(tk.END, "ОШИБКА ПОДКЛЮЧЕНИЯ\n")
            self.results_text.insert(tk.END, f"{'='*80}\n\n")
            self.results_text.insert(tk.END, f"База данных '{SQL_DATABASE}' не найдена или недоступна.\n")
            self.results_text.insert(tk.END, "Убедитесь, что:\n")
            self.results_text.insert(tk.END, f"1. База данных '{SQL_DATABASE}' существует на сервере\n")
            self.results_text.insert(tk.END, "2. У вас есть права доступа к этой базе\n")
            self.results_text.insert(tk.END, "3. Сервер доступен и работает\n")
            self.status_var.set(f"База данных '{SQL_DATABASE}' не найдена")
            return
        
        if not results:
            self.results_text.insert(tk.END, f"{'='*80}\n")
            self.results_text.insert(tk.END, "РЕЗУЛЬТАТЫ ПОИСКА\n")
            self.results_text.insert(tk.END, f"{'='*80}\n\n")
            self.results_text.insert(tk.END, f"Клиенты с email '{email_address}' не найдены.\n")
            self.status_var.set(f"Клиенты не найдены")
            return
        
        # Отображаем найденные записи
        self.results_text.insert(tk.END, f"{'='*80}\n")
        self.results_text.insert(tk.END, "РЕЗУЛЬТАТЫ ПОИСКА\n")
        self.results_text.insert(tk.END, f"{'='*80}\n\n")
        self.results_text.insert(tk.END, f"Найдено записей: {len(results)}\n\n")
        
        for i, row in enumerate(results, 1):
            self.results_text.insert(tk.END, f"{'-'*80}\n")
            self.results_text.insert(tk.END, f"ЗАПИСЬ #{i}\n")
            self.results_text.insert(tk.END, f"{'-'*80}\n\n")
            
            # Отображаем все поля записи
            for key, value in row.items():
                if value is not None:
                    display_value = str(value)
                    if len(display_value) > 100:
                        display_value = display_value[:100] + "..."
                    self.results_text.insert(tk.END, f"{key}: {display_value}\n")
            self.results_text.insert(tk.END, "\n")
        
        self.results_text.insert(tk.END, f"{'='*80}\n")
        self.results_text.insert(tk.END, "КОНЕЦ РЕЗУЛЬТАТОВ\n")
        self.results_text.insert(tk.END, f"{'='*80}\n")
        
        self.status_var.set(f"Найдено записей: {len(results)}")
        
        # Прокручиваем в начало
        self.results_text.see(1.0)
    
    def _show_error(self, error_message):
        """Показывает ошибку"""
        self.results_text.insert(tk.END, f"{'='*80}\n")
        self.results_text.insert(tk.END, "ОШИБКА ПРИ ВЫПОЛНЕНИИ ЗАПРОСА\n")
        self.results_text.insert(tk.END, f"{'='*80}\n\n")
        self.results_text.insert(tk.END, f"Сообщение об ошибке:\n{error_message}\n")
        self.status_var.set("Ошибка при выполнении запроса")
    
    def clear_results(self):
        """Очищает результаты поиска"""
        self.results_text.delete(1.0, tk.END)
        self.status_var.set("Результаты очищены")
    
    def copy_results(self):
        """Копирует результаты в буфер обмена"""
        try:
            results_text = self.results_text.get(1.0, tk.END)
            if results_text.strip():
                self.window.clipboard_clear()
                self.window.clipboard_append(results_text)
                self.status_var.set("Результаты скопированы в буфер обмена")
            else:
                messagebox.showinfo("Информация", "Нет данных для копирования")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать: {e}")
    
    def export_results(self):
        """Экспортирует результаты в файл"""
        try:
            results_text = self.results_text.get(1.0, tk.END)
            if not results_text.strip():
                messagebox.showinfo("Информация", "Нет данных для экспорта")
                return
            
            # Создаем файл в домашней директории
            home_dir = os.path.expanduser("~")
            filename = os.path.join(home_dir, f"dog_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(results_text)
            
            self.status_var.set(f"Результаты экспортированы в: {filename}")
            messagebox.showinfo("Экспорт завершен", f"Данные экспортированы в файл:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать: {e}")

# ============================================
# ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ
# ============================================

class OblgazEmailFetcher:
    def __init__(self, root):
        self.root = root
        self.root.title("Oblgaz Email Fetcher")
        self.root.geometry("1200x800")
        
        # Устанавливаем иконку
        try:
            self.root.iconname("oblgaz-fetcher")
        except:
            pass
        
        # Настраиваем прокси
        self.setup_proxy()
        
        # Проверяем подключение к БД DOG
        self.check_db_connection()
        
        # Настройка интерфейса
        self.setup_ui()
        
        # Авто-тест подключения
        self.root.after(1000, self.auto_test_connection)
    
    def setup_proxy(self):
        """Настраивает прокси"""
        self.proxy_status = setup_mail_proxy()
        
    def check_db_connection(self):
        """Проверяет подключение к базе данных DOG"""
        print("Проверка подключения к базе данных...")
        self.db_status = check_dog_database()
        
        if self.db_status:
            print(f"✓ База данных '{SQL_DATABASE}' доступна")
            self.db_available = True
        else:
            print("× База данных недоступна")
            self.db_available = False
    
    def auto_test_connection(self):
        """Автоматический тест подключения при запуске"""
        self.log_message("=" * 60)
        self.log_message("АВТОМАТИЧЕСКИЙ ТЕСТ ПОДКЛЮЧЕНИЙ")
        
        # Тест прокси
        if self.proxy_status:
            self.proxy_status_var.set("Прокси: Настроен")
            self.log_message("Прокси настроен")
        else:
            self.proxy_status_var.set("Прокси: Ошибка")
            self.log_message("Ошибка настройки прокси")
        
        # Тест БД
        if self.db_available:
            self.db_status_var.set(f"БД: {SQL_DATABASE}")
            self.log_message(f"База данных '{SQL_DATABASE}' доступна")
        else:
            self.db_status_var.set("БД: Недоступна")
            self.log_message("База данных недоступна")
        
        # Тест почты (в фоне)
        threading.Thread(target=self.test_mail_background, daemon=True).start()
    
    def test_mail_background(self):
        """Фоновый тест почтового подключения"""
        try:
            self.log_message("Тестирование подключения к почте...")
            
            mail = get_imap_connection_oblgaz()
            if mail:
                # Проверяем доступные папки
                status, folders = mail.list()
                if status == 'OK':
                    folder_list = []
                    for folder in folders:
                        try:
                            folder_str = folder.decode('utf-8', errors='ignore')
                            # Извлекаем имя папки
                            match = re.search(r'\"([^\"]+)\"$', folder_str)
                            if match:
                                folder_list.append(match.group(1))
                        except:
                            continue
                    
                    self.log_message(f"Почта подключена. Папок: {len(folder_list)}")
                    if folder_list:
                        self.log_message(f"   Доступные папки: {', '.join(folder_list[:5])}")
                
                mail.logout()
                self.mail_status_var.set("Почта: Доступна")
                self.status_var.set("Все системы готовы")
            else:
                self.log_message("Не удалось подключиться к почте")
                self.mail_status_var.set("Почта: Ошибка")
                self.status_var.set("Проверьте подключение")
                
        except Exception as e:
            self.log_message(f"Ошибка теста почты: {e}")
            self.mail_status_var.set("Почта: Ошибка")
    
    def setup_ui(self):
        """Настраивает пользовательский интерфейс"""
        # Стиль
        style = ttk.Style()
        style.theme_use('clam')
        
        # Главный контейнер
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Левая панель - управление
        left_panel = ttk.LabelFrame(main_frame, text="Управление", padding="15")
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        
        # Правая панель - информация
        right_panel = ttk.LabelFrame(main_frame, text="Информация", padding="15")
        right_panel.pack(side="right", fill="both", expand=True)
        
        # ===== ЛЕВАЯ ПАНЕЛЬ =====
        
        # Информация о сервере
        server_info = ttk.LabelFrame(left_panel, text="Информация о сервере", padding="10")
        server_info.pack(fill="x", pady=(0, 15))
        
        info_lines = [
            f"Сервер: {MAIL_SERVER}",
            f"SMTP порт: {SMTP_PORT} (STARTTLS)",
            f"IMAP порт: {IMAP_PORT} (SSL)",
            f"Пользователь: {USERNAME}",
            f"Целевой отправитель: {TARGET_SENDER}",
            f"Прокси: {PROXY_HOST}:{PROXY_PORT}",
            f"SQL Server: {SQL_SERVER}:{SQL_PORT}",
            f"База данных: {SQL_DATABASE}"
        ]
        
        for line in info_lines:
            lbl = tk.Label(server_info, text=line, anchor="w", justify="left")
            lbl.pack(fill="x", pady=2)
        
        # Параметры поиска
        search_frame = ttk.LabelFrame(left_panel, text="Параметры поиска", padding="10")
        search_frame.pack(fill="x", pady=(0, 15))
        
        # Период поиска
        ttk.Label(search_frame, text="Период поиска:").grid(row=0, column=0, sticky="w", pady=5)
        self.days_var = tk.StringVar(value="30")
        days_combo = ttk.Combobox(search_frame, textvariable=self.days_var, 
                                 values=["1", "7", "30", "90", "180", "365"], width=10)
        days_combo.grid(row=0, column=1, pady=5, padx=5)
        
        # Папка для поиска
        ttk.Label(search_frame, text="Папка:").grid(row=1, column=0, sticky="w", pady=5)
        self.folder_var = tk.StringVar(value="INBOX")
        folder_combo = ttk.Combobox(search_frame, textvariable=self.folder_var, 
                                   values=["INBOX", "Sent", "Drafts", "Trash"], width=10)
        folder_combo.grid(row=1, column=1, pady=5, padx=5)
        
        # Максимум писем
        ttk.Label(search_frame, text="Макс. писем:").grid(row=2, column=0, sticky="w", pady=5)
        self.limit_var = tk.StringVar(value="50")
        limit_combo = ttk.Combobox(search_frame, textvariable=self.limit_var, 
                                  values=["10", "25", "50", "100", "500"], width=10)
        limit_combo.grid(row=2, column=1, pady=5, padx=5)
        
        # Кнопки управления
        buttons_frame = ttk.Frame(left_panel)
        buttons_frame.pack(fill="x", pady=(10, 0))
        
        button_configs = [
            ("Тест подключений", self.test_all_connections, "#2196F3"),
            ("Получить письма", self.start_fetch_emails, "#4CAF50"),
            ("Работа в БД", self.open_db_work_window, "#3498db"),
            ("Очистить логи", self.clear_logs, "#f44336"),
            ("Системная информация", self.show_sys_info, "#607D8B")
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
                width=20
            )
            btn.pack(pady=5)
            btn.bind("<Enter>", lambda e, b=btn: b.config(background="#555"))
            btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(background=c))
        
        # ===== ПРАВАЯ ПАНЕЛЬ =====
        
        # Статус бар
        status_frame = tk.Frame(right_panel)
        status_frame.config(background="#f0f0f0", pady=10)
        status_frame.pack(fill="x", pady=(0, 10))
        
        self.proxy_status_var = tk.StringVar(value="Прокси: Проверка...")
        self.db_status_var = tk.StringVar(value="БД: Проверка...")
        self.mail_status_var = tk.StringVar(value="Почта: Проверка...")
        
        status_labels = [
            (self.proxy_status_var, "#2196F3"),
            (self.db_status_var, "#4CAF50"),
            (self.mail_status_var, "#FF9800"),
        ]
        
        for var, color in status_labels:
            lbl = tk.Label(status_frame, textvariable=var)
            lbl.config(
                background=color,
                foreground="white",
                font=("Arial", 10),
                padx=15,
                pady=8,
                relief="ridge"
            )
            lbl.pack(side="left", padx=5)
        
        # Вкладки
        notebook = ttk.Notebook(right_panel)
        notebook.pack(fill="both", expand=True)
        
        # Вкладка: Письма
        emails_tab = ttk.Frame(notebook)
        notebook.add(emails_tab, text="Письма")
        
        # Панель инструментов для писем
        emails_toolbar = tk.Frame(emails_tab)
        emails_toolbar.config(background="#e0e0e0", pady=5)
        emails_toolbar.pack(fill="x")
        
        refresh_btn = tk.Button(emails_toolbar, text="Обновить", command=self.start_fetch_emails)
        refresh_btn.config(
            background="#4CAF50",
            foreground="white",
            relief="flat",
            padx=10
        )
        refresh_btn.pack(side="left", padx=5)
        
        clear_btn = tk.Button(emails_toolbar, text="Очистить", 
                 command=lambda: self.emails_area.delete(1.0, tk.END))
        clear_btn.config(
            background="#f44336",
            foreground="white",
            relief="flat",
            padx=10
        )
        clear_btn.pack(side="left", padx=5)
        
        # Область для отображения писем
        self.emails_area = scrolledtext.ScrolledText(
            emails_tab,
            wrap=tk.WORD,
            font=("DejaVu Sans Mono", 10)
        )
        self.emails_area.config(
            background="#fafafa",
            padx=10,
            pady=10
        )
        self.emails_area.pack(fill="both", expand=True)
        
        # Вкладка: Логи
        logs_tab = ttk.Frame(notebook)
        notebook.add(logs_tab, text="Логи")
        
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
        self.logs_area.pack(fill="both", expand=True)
        
        # Прогресс бар
        progress_frame = tk.Frame(right_panel)
        progress_frame.pack(fill="x", pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=500,
            mode='determinate'
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.progress_label = tk.Label(progress_frame, text="0%", font=("Arial", 10))
        self.progress_label.pack(side="right")
        
        # Статусная строка
        self.status_var = tk.StringVar(value="Инициализация...")
        status_bar = tk.Label(
            right_panel,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w"
        )
        status_bar.config(
            background="#e8e8e8",
            padx=15,
            pady=8,
            font=("Arial", 10)
        )
        status_bar.pack(side="bottom", fill="x")
        
    def open_db_work_window(self):
        """Открывает окно для работы с БД"""
        try:
            # Создаем новое окно
            db_window = DatabaseWorkWindow(self.root)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть окно работы с БД:\n{e}")
    
    def log_message(self, message):
        """Добавляет сообщение в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        self.logs_area.insert(tk.END, log_entry + "\n")
        self.logs_area.see(tk.END)
        
        # Также выводим в консоль
        print(log_entry)
        
        # Обновляем интерфейс
        self.root.update_idletasks()
    
    def test_all_connections(self):
        """Тестирует все подключения"""
        self.log_message("=" * 60)
        self.log_message("ПОЛНЫЙ ТЕСТ ПОДКЛЮЧЕНИЙ")
        
        # Сбрасываем статусы
        self.proxy_status_var.set("Прокси: Тестируется...")
        self.db_status_var.set("БД: Тестируется...")
        self.mail_status_var.set("Почта: Тестируется...")
        self.status_var.set("Выполняется тестирование...")
        
        # Тест в отдельных потоках
        threads = []
        
        # Тест прокси
        t1 = threading.Thread(target=self.test_proxy_thread, daemon=True)
        threads.append(t1)
        
        # Тест БД
        t2 = threading.Thread(target=self.test_db_thread, daemon=True)
        threads.append(t2)
        
        # Тест почты
        t3 = threading.Thread(target=self.test_mail_thread, daemon=True)
        threads.append(t3)
        
        # Запускаем все тесты
        for t in threads:
            t.start()
        
        # Ждем завершения
        for t in threads:
            t.join(timeout=30)
        
        self.log_message("=" * 60)
        self.log_message("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        self.status_var.set("Тестирование завершено")
    
    def test_proxy_thread(self):
        """Тестирует подключение прокси"""
        try:
            import urllib.request
            
            proxy_handler = urllib.request.ProxyHandler({
                'http': f'http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}',
                'https': f'http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}'
            })
            
            opener = urllib.request.build_opener(proxy_handler)
            response = opener.open('http://httpbin.org/ip', timeout=10)
            ip_info = response.read().decode()
            
            self.proxy_status_var.set("Прокси: Работает")
            self.log_message(f"Прокси: {ip_info[:50]}...")
            
        except Exception as e:
            self.proxy_status_var.set("Прокси: Ошибка")
            self.log_message(f"Прокси ошибка: {e}")
    
    def test_db_thread(self):
        """Тестирует подключение к БД"""
        # Повторно проверяем подключение к БД
        self.check_db_connection()
        
        if self.db_available:
            self.db_status_var.set(f"БД: {SQL_DATABASE}")
            self.log_message(f"База данных '{SQL_DATABASE}' доступна")
            
            # Проверяем наличие таблицы
            conn = get_sql_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT TABLE_NAME 
                        FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_NAME = 'srv_client_fl'
                    """)
                    
                    if cursor.fetchone():
                        self.log_message("Таблица srv_client_fl найдена")
                    else:
                        self.log_message("Таблица srv_client_fl не найдена")
                        
                except Exception as e:
                    self.log_message(f"Ошибка проверки таблиц: {e}")
                finally:
                    conn.close()
        else:
            self.db_status_var.set("БД: Недоступна")
            self.log_message("База данных недоступна")
    
    def test_mail_thread(self):
        """Тестирует подключение к почте"""
        try:
            mail = get_imap_connection_oblgaz()
            if mail:
                # Получаем список папок
                status, folders = mail.list()
                if status == 'OK':
                    folder_count = len(folders)
                    self.mail_status_var.set(f"Почта: {folder_count} папок")
                    self.log_message(f"Почта подключена, папок: {folder_count}")
                    
                    # Показываем первые 3 папки
                    for i, folder in enumerate(folders[:3]):
                        try:
                            folder_name = folder.decode('utf-8', errors='ignore')
                            self.log_message(f"   {folder_name[:60]}")
                        except:
                            pass
                else:
                    self.mail_status_var.set("Почта: Ошибка папок")
                    self.log_message("Не удалось получить список папок")
                
                mail.logout()
            else:
                self.mail_status_var.set("Почта: Ошибка")
                self.log_message("Не удалось подключиться к почтовому серверу")
                
        except Exception as e:
            self.mail_status_var.set("Почта: Ошибка")
            self.log_message(f"Ошибка теста почты: {e}")
    
    def start_fetch_emails(self):
        """Запускает получение писем"""
        if hasattr(self, '_fetching') and self._fetching:
            self.log_message("Получение писем уже выполняется")
            return
        
        self._fetching = True
        threading.Thread(target=self.fetch_emails, daemon=True).start()
    
    def fetch_emails(self):
        """Получает письма с сервера"""
        try:
            self.emails_area.delete(1.0, tk.END)
            self.progress_var.set(0)
            self.progress_label.config(text="0%")
            self.status_var.set("Подключение к почтовому серверу...")
            
            self.log_message("=" * 60)
            self.log_message("НАЧАЛО ПОЛУЧЕНИЯ ПИСЕМ")
            self.log_message(f"Отправитель: {TARGET_SENDER}")
            
            # Подключаемся к IMAP
            mail = get_imap_connection_oblgaz()
            if not mail:
                self.log_message("Не удалось подключиться к почтовому серверу")
                self.status_var.set("Ошибка подключения")
                self._fetching = False
                return
            
            # Выбираем папку
            folder = self.folder_var.get()
            try:
                status, data = mail.select(folder)
                if status == 'OK':
                    self.log_message(f"Выбрана папка: {folder}")
                else:
                    # Пробуем INBOX если выбранная папка не работает
                    mail.select('INBOX')
                    self.log_message(f"Папка {folder} недоступна, используем INBOX")
                    folder = 'INBOX'
            except:
                mail.select('INBOX')
                self.log_message(f"Ошибка выбора папки, используем INBOX")
                folder = 'INBOX'
            
            # Формируем критерий поиска
            days = int(self.days_var.get())
            since_date = (datetime.now() - timedelta(days=days)).strftime('%d-%b-%Y')
            search_criteria = f'(SINCE "{since_date}")'
            
            if TARGET_SENDER:
                search_criteria = f'(FROM "{TARGET_SENDER}" {search_criteria})'
            
            self.log_message(f"Критерий поиска: {search_criteria}")
            
            # Ищем письма
            self.status_var.set("Поиск писем...")
            status, email_ids = mail.search(None, search_criteria)
            
            if status != 'OK' or not email_ids[0]:
                self.log_message("Писем не найдено")
                self.emails_area.insert(tk.END, f"Писем от {TARGET_SENDER} не найдено\n")
                mail.logout()
                self.status_var.set("Писем не найдено")
                self._fetching = False
                return
            
            email_ids = email_ids[0].split()
            total_emails = len(email_ids)
            
            self.log_message(f"Найдено писем: {total_emails}")
            
            # Ограничиваем количество обрабатываемых писем
            limit = int(self.limit_var.get())
            if total_emails > limit:
                email_ids = email_ids[-limit:]  # Берем последние письма
                self.log_message(f"Ограничение: обработаем {limit} последних писем")
            
            emails_to_process = len(email_ids)
            
            self.status_var.set(f"Обработка {emails_to_process} писем...")
            
            # Обрабатываем письма
            for i, email_id in enumerate(email_ids):
                # Обновляем прогресс
                progress = (i + 1) / emails_to_process * 100
                self.progress_var.set(progress)
                self.progress_label.config(text=f"{int(progress)}%")
                
                try:
                    # Получаем письмо
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    
                    if status == 'OK':
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        
                        # Обрабатываем письмо
                        email_data = self.process_email_message(msg, email_id.decode(), folder)
                        
                        # Отображаем в интерфейсе
                        self.display_email(email_data, i + 1)
                        
                except Exception as e:
                    self.log_message(f"Ошибка обработки письма {email_id}: {e}")
            
            # Итоги
            self.log_message("=" * 60)
            self.log_message(f"ОБРАБОТКА ЗАВЕРШЕНА")
            self.log_message(f"Обработано: {emails_to_process} писем")
            
            self.emails_area.insert(tk.END, f"\n{'═'*60}\n")
            self.emails_area.insert(tk.END, f"ИТОГИ ОБРАБОТКИ\n")
            self.emails_area.insert(tk.END, f"• Обработано писем: {emails_to_process}\n")
            self.emails_area.insert(tk.END, f"• Отправитель: {TARGET_SENDER}\n")
            self.emails_area.insert(tk.END, f"• Период: последние {days} дней\n")
            self.emails_area.insert(tk.END, f"• Папка: {folder}\n")
            
            self.status_var.set(f"Готово. Обработано: {emails_to_process}")
            
            # Закрываем соединение
            mail.close()
            mail.logout()
            self.log_message("Соединение закрыто")
            
        except Exception as e:
            self.log_message(f"Критическая ошибка: {e}")
            import traceback
            self.log_message(f"Трассировка:\n{traceback.format_exc()}")
            self.status_var.set("Ошибка выполнения")
        
        finally:
            self._fetching = False
    
    def process_email_message(self, msg, email_id, folder):
        """Обрабатывает email сообщение"""
        # Базовые заголовки
        message_id = msg.get('Message-ID', '')
        subject = msg.get('Subject', 'Без темы')
        date_received = msg.get('Date', '')
        from_header = msg.get('From', '')
        to_header = msg.get('To', USERNAME)
        
        # Декодируем тему
        if subject:
            decoded_subject, encoding = decode_header(subject)[0]
            if isinstance(decoded_subject, bytes):
                subject = decoded_subject.decode(encoding if encoding else 'utf-8', errors='ignore')
        
        # Декодируем отправителя
        sender_email = ''
        sender_name = ''
        if from_header:
            decoded_from, encoding = decode_header(from_header)[0]
            if isinstance(decoded_from, bytes):
                from_header = decoded_from.decode(encoding if encoding else 'utf-8', errors='ignore')
            
            # Извлекаем email и имя
            if '<' in from_header and '>' in from_header:
                parts = from_header.split('<')
                sender_name = parts[0].strip(' "\'')
                sender_email = parts[1].split('>')[0].strip()
            else:
                sender_email = from_header
                sender_name = from_header
        
        # Определяем важность
        importance = 'normal'
        importance_header = msg.get('Importance', '').lower()
        if 'high' in importance_header:
            importance = 'high'
        elif 'low' in importance_header:
            importance = 'low'
        
        # Извлекаем содержимое
        body_text = ''
        body_html = ''
        has_attachment = False
        attachment_count = 0
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))
                
                # Проверяем вложения
                if 'attachment' in content_disposition.lower():
                    has_attachment = True
                    attachment_count += 1
                    continue
                
                # Текстовое содержимое
                if content_type == 'text/plain':
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_text = payload.decode('utf-8', errors='ignore')
                    except:
                        pass
                
                elif content_type == 'text/html':
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_html = payload.decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            # Простое письмо
            content_type = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    if content_type == 'text/plain':
                        body_text = payload.decode('utf-8', errors='ignore')
                    elif content_type == 'text/html':
                        body_html = payload.decode('utf-8', errors='ignore')
                    else:
                        body_text = str(payload)
            except:
                body_text = str(msg.get_payload())
        
        # Очищаем текст
        if body_text:
            body_text = ' '.join(body_text.split())
        
        return {
            'email_id': email_id,
            'message_id': message_id,
            'sender_email': sender_email,
            'sender_name': sender_name,
            'recipient_email': USERNAME,
            'subject': subject,
            'date_received': parse_email_date(date_received),
            'body_text': body_text[:4000],
            'body_html': body_html[:4000],
            'has_attachment': 1 if has_attachment else 0,
            'attachment_count': attachment_count,
            'importance': importance,
            'folder': folder,
            'is_read': 0
        }
    
    def display_email(self, email_data, index):
        """Отображает письмо в интерфейсе"""
        self.emails_area.insert(tk.END, f"\n{'='*60}\n")
        self.emails_area.insert(tk.END, f"ПИСЬМО #{index}\n\n")
        
        # Основная информация
        self.emails_area.insert(tk.END, f"Тема: {email_data['subject']}\n")
        self.emails_area.insert(tk.END, f"Дата: {email_data['date_received']}\n")
        self.emails_area.insert(tk.END, f"От: {email_data['sender_name']}\n")
        self.emails_area.insert(tk.END, f"Email: {email_data['sender_email']}\n")
        
        if email_data['has_attachment']:
            self.emails_area.insert(tk.END, f"Вложений: {email_data['attachment_count']}\n")
        
        # Показываем первые 2 письма подробно
        if index <= 2 and email_data['body_text']:
            preview = email_data['body_text']
            if len(preview) > 300:
                preview = preview[:300] + "..."
            
            self.emails_area.insert(tk.END, f"\nСодержание:\n{preview}\n")
        
        self.emails_area.see(tk.END)
        self.root.update_idletasks()
    
    def clear_logs(self):
        """Очищает логи"""
        self.logs_area.delete(1.0, tk.END)
        self.log_message("Логи очищены")
    
    def show_sys_info(self):
        """Показывает системную информацию"""
        info = f"""
=== СИСТЕМНАЯ ИНФОРМАЦИЯ ===

ОС: {sys.platform}
Python: {sys.version}
Текущая директория: {os.getcwd()}
Время: {datetime.now()}

=== НАСТРОЙКИ СЕРВЕРА ===

Почтовый сервер: {MAIL_SERVER}
SMTP порт: {SMTP_PORT} (STARTTLS)
IMAP порт: {IMAP_PORT} (SSL)
Пользователь: {USERNAME}
Целевой отправитель: {TARGET_SENDER}

=== ПРОКСИ ===

Хост: {PROXY_HOST}:{PROXY_PORT}
Пользователь: {PROXY_USER}

=== БАЗА ДАННЫХ ===

SQL Server: {SQL_SERVER}:{SQL_PORT}
База: {SQL_DATABASE}
Пользователь: {SQL_USERNAME}
Статус БД: {"Доступна" if self.db_available else "Недоступна"}
"""
        
        self.emails_area.delete(1.0, tk.END)
        self.emails_area.insert(tk.END, info)
        self.log_message("Показана системная информация")

# ============================================
# ЗАПУСК ПРОГРАММЫ
# ============================================

def main():
    """Главная функция запуска"""
    print("\n" + "="*70)
    print("OBLGAZ EMAIL FETCHER ДЛЯ REDOS/LINUX")
    print("="*70)
    
    # Проверяем зависимости
    if not check_linux_dependencies():
        print("\nУстановите зависимости и перезапустите программу")
        sys.exit(1)
    
    print("Зависимости проверены")
    
    # Проверяем DISPLAY для GUI
    if 'DISPLAY' not in os.environ:
        print("Внимание: Переменная DISPLAY не установлена")
        os.environ['DISPLAY'] = ':0'
    
    try:
        # Создаем главное окно
        root = tk.Tk()
        
        # Центрируем окно
        window_width = 1200
        window_height = 800
        
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        
        root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        # Создаем приложение
        app = OblgazEmailFetcher(root)
        
        # Запускаем главный цикл
        print("GUI загружается...")
        print("="*70)
        root.mainloop()
        
    except tk.TclError as e:
        if "display" in str(e).lower():
            print(f"\nОшибка GUI: {e}")
            print("\nРешения:")
            print("  1. Запустите на машине с GUI")
            print("  2. Или используйте ssh -X для удаленного доступа")
        else:
            print(f"Ошибка Tkinter: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()