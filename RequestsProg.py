#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import imaplib
import smtplib
import email
import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
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
SQL_DATABASE = 'EmailDB'
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

def get_sql_connection():
    """Подключается к SQL Server"""
    try:
        # ИСПРАВЛЕНИЕ: Проверяем подключение к базе master сначала
        # Если база EmailDB не существует, создаем ее
        try:
            conn = pymssql.connect(
                server=SQL_SERVER,
                port=SQL_PORT,
                user=SQL_USERNAME,
                password=SQL_PASSWORD,
                database=SQL_DATABASE,
                charset='UTF-8',
                login_timeout=15
            )
            return conn
        except pymssql.OperationalError as e:
            if "database" in str(e).lower() or "18456" in str(e):
                print(f"Предупреждение: {e}")
                print("Пробуем подключиться к базе 'master'...")
                
                # Пробуем подключиться к master
                conn = pymssql.connect(
                    server=SQL_SERVER,
                    port=SQL_PORT,
                    user=SQL_USERNAME,
                    password=SQL_PASSWORD,
                    database='master',
                    charset='UTF-8',
                    login_timeout=15
                )
                
                # Проверяем существование базы EmailDB
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sys.databases WHERE name = 'EmailDB'")
                db_exists = cursor.fetchone()
                
                if not db_exists:
                    print("База EmailDB не существует, создаем...")
                    cursor.execute("CREATE DATABASE EmailDB")
                    conn.commit()
                    print("База EmailDB создана")
                
                cursor.close()
                conn.close()
                
                # Теперь подключаемся к EmailDB
                return pymssql.connect(
                    server=SQL_SERVER,
                    port=SQL_PORT,
                    user=SQL_USERNAME,
                    password=SQL_PASSWORD,
                    database=SQL_DATABASE,
                    charset='UTF-8',
                    login_timeout=15
                )
            else:
                raise
    except Exception as e:
        print(f"Ошибка подключения к SQL Server: {e}")
        return None

def init_database():
    """Инициализирует базу данных"""
    conn = get_sql_connection()
    if not conn:
        print("Не удалось подключиться к SQL Server")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Проверяем, к какой базе подключились
        cursor.execute("SELECT DB_NAME() as db_name")
        current_db = cursor.fetchone()[0]
        print(f"Текущая база данных: {current_db}")
        
        # Создаем таблицу если не существует
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES 
                          WHERE TABLE_NAME = 'oblgaz_emails')
            BEGIN
                CREATE TABLE oblgaz_emails (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    email_id NVARCHAR(255),
                    message_id NVARCHAR(500),
                    sender_email NVARCHAR(255),
                    sender_name NVARCHAR(255),
                    recipient_email NVARCHAR(255),
                    subject NVARCHAR(MAX),
                    date_received DATETIME,
                    body_text NVARCHAR(MAX),
                    body_html NVARCHAR(MAX),
                    has_attachment BIT DEFAULT 0,
                    attachment_count INT DEFAULT 0,
                    importance NVARCHAR(20),
                    folder NVARCHAR(100),
                    fetched_date DATETIME DEFAULT GETDATE(),
                    processed_date DATETIME NULL,
                    is_read BIT DEFAULT 0
                )
                
                -- Создаем индексы для быстрого поиска
                CREATE INDEX idx_sender_email ON oblgaz_emails(sender_email)
                CREATE INDEX idx_date_received ON oblgaz_emails(date_received)
                CREATE INDEX idx_fetched_date ON oblgaz_emails(fetched_date)
                CREATE INDEX idx_folder ON oblgaz_emails(folder)
                
                PRINT 'Таблица oblgaz_emails создана'
            END
            ELSE
            BEGIN
                PRINT 'Таблица oblgaz_emails уже существует'
            END
        """)
        
        conn.commit()
        
        # Проверяем количество записей
        cursor.execute("SELECT COUNT(*) as cnt FROM oblgaz_emails")
        count = cursor.fetchone()[0]
        print(f"База данных инициализирована, записей: {count}")
        return True
        
    except Exception as e:
        print(f"Ошибка инициализации БД: {e}")
        
        # Попробуем создать простую таблицу
        try:
            cursor.execute("""
                CREATE TABLE oblgaz_emails (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    email_id NVARCHAR(255),
                    sender_email NVARCHAR(255),
                    sender_name NVARCHAR(255),
                    subject NVARCHAR(MAX),
                    date_received DATETIME,
                    body_text NVARCHAR(MAX),
                    fetched_date DATETIME DEFAULT GETDATE()
                )
            """)
            conn.commit()
            print("Таблица oblgaz_emails создана (упрощенная версия)")
            return True
        except Exception as e2:
            print(f"Не удалось создать таблицу: {e2}")
            return False
    finally:
        conn.close()

def save_email_to_db(email_data):
    """Сохраняет письмо в базу данных"""
    conn = get_sql_connection()
    if not conn:
        print("Нет подключения к БД для сохранения")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже такое письмо
        cursor.execute("""
            SELECT id FROM oblgaz_emails 
            WHERE email_id = %s
        """, (email_data.get('email_id'),))
        
        existing = cursor.fetchone()
        
        if not existing:
            # Вставляем новую запись
            cursor.execute("""
                INSERT INTO oblgaz_emails (
                    email_id, message_id, sender_email, sender_name,
                    recipient_email, subject, date_received,
                    body_text, body_html, has_attachment, attachment_count,
                    importance, folder, is_read
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                email_data.get('email_id'),
                email_data.get('message_id', ''),
                email_data.get('sender_email', ''),
                email_data.get('sender_name', ''),
                email_data.get('recipient_email', USERNAME),
                email_data.get('subject', 'Без темы'),
                email_data.get('date_received'),
                email_data.get('body_text', ''),
                email_data.get('body_html', ''),
                email_data.get('has_attachment', 0),
                email_data.get('attachment_count', 0),
                email_data.get('importance', 'normal'),
                email_data.get('folder', 'INBOX'),
                email_data.get('is_read', 0)
            ))
            
            conn.commit()
            print(f"Письмо сохранено: {email_data.get('subject', '')[:50]}...")
            return True
        else:
            print(f"Письмо уже существует в БД: ID {existing[0]}")
            return False
            
    except Exception as e:
        print(f"Ошибка сохранения в БД: {e}")
        return False
    finally:
        conn.close()

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
        
        # Инициализируем БД
        self.init_db()
        
        # Настройка интерфейса
        self.setup_ui()
        
        # Авто-тест подключения
        self.root.after(1000, self.auto_test_connection)
    
    def setup_proxy(self):
        """Настраивает прокси"""
        self.proxy_status = setup_mail_proxy()
        
    def init_db(self):
        """Инициализирует базу данных"""
        self.db_status = init_database()
    
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
        if self.db_status:
            self.db_status_var.set("БД: Готова")
            self.log_message("База данных готова")
        else:
            self.db_status_var.set("БД: Ошибка")
            self.log_message("Ошибка инициализации БД")
        
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
            f"SQL Server: {SQL_SERVER}:{SQL_PORT}"
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
            ("Обновить статистику", self.update_stats, "#FF9800"),
            ("Очистить логи", self.clear_logs, "#f44336"),
            ("Экспорт в CSV", self.export_to_csv, "#9C27B0"),
            ("Системная информация", self.show_sys_info, "#607D8B")
        ]
        
        for text, command, color in button_configs:
            btn = tk.Button(buttons_frame, text=text, command=command,
                          bg=color, fg="white", font=("Arial", 10, "bold"),
                          relief="flat", padx=15, pady=10, width=20)
            btn.pack(pady=5)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#555"))
            btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(bg=c))
        
        # ===== ПРАВАЯ ПАНЕЛЬ =====
        
        # Статус бар
        status_frame = tk.Frame(right_panel, bg="#f0f0f0", pady=10)
        status_frame.pack(fill="x", pady=(0, 10))
        
        self.proxy_status_var = tk.StringVar(value="Прокси: Проверка...")
        self.db_status_var = tk.StringVar(value="БД: Проверка...")
        self.mail_status_var = tk.StringVar(value="Почта: Проверка...")
        self.total_emails_var = tk.StringVar(value="Всего: 0")
        
        status_labels = [
            (self.proxy_status_var, "#2196F3"),
            (self.db_status_var, "#4CAF50"),
            (self.mail_status_var, "#FF9800"),
            (self.total_emails_var, "#9C27B0")
        ]
        
        for var, color in status_labels:
            lbl = tk.Label(status_frame, textvariable=var, bg=color, fg="white",
                         font=("Arial", 10), padx=15, pady=8, relief="ridge")
            lbl.pack(side="left", padx=5)
        
        # Вкладки
        notebook = ttk.Notebook(right_panel)
        notebook.pack(fill="both", expand=True)
        
        # Вкладка: Письма
        emails_tab = ttk.Frame(notebook)
        notebook.add(emails_tab, text="Письма")
        
        # Панель инструментов для писем
        emails_toolbar = tk.Frame(emails_tab, bg="#e0e0e0", pady=5)
        emails_toolbar.pack(fill="x")
        
        tk.Button(emails_toolbar, text="Обновить", command=self.start_fetch_emails,
                 bg="#4CAF50", fg="white", relief="flat", padx=10).pack(side="left", padx=5)
        tk.Button(emails_toolbar, text="Очистить", 
                 command=lambda: self.emails_area.delete(1.0, tk.END),
                 bg="#f44336", fg="white", relief="flat", padx=10).pack(side="left", padx=5)
        
        # Область для отображения писем
        self.emails_area = scrolledtext.ScrolledText(
            emails_tab,
            wrap=tk.WORD,
            font=("DejaVu Sans Mono", 10),
            bg="#fafafa",
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
            font=("DejaVu Sans Mono", 9),
            bg="#1e1e1e",
            fg="#00ff00",
            padx=10,
            pady=10
        )
        self.logs_area.pack(fill="both", expand=True)
        
        # Вкладка: Статистика
        stats_tab = ttk.Frame(notebook)
        notebook.add(stats_tab, text="Статистика")
        
        self.stats_area = scrolledtext.ScrolledText(
            stats_tab,
            wrap=tk.WORD,
            font=("DejaVu Sans Mono", 10),
            bg="#e8f4f8",
            padx=10,
            pady=10
        )
        self.stats_area.pack(fill="both", expand=True)
        
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
            anchor="w",
            bg="#e8e8e8",
            padx=15,
            pady=8,
            font=("Arial", 10)
        )
        status_bar.pack(side="bottom", fill="x")
        
        # Инициализируем статистику
        self.update_stats()
    
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
        conn = get_sql_connection()
        if conn:
            try:
                cursor = conn.cursor()
                
                # Проверяем версию сервера
                cursor.execute("SELECT @@VERSION as version")
                version = cursor.fetchone()[0]
                
                # Проверяем таблицу
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = 'oblgaz_emails'
                """)
                table_exists = cursor.fetchone()[0] > 0
                
                if table_exists:
                    cursor.execute("SELECT COUNT(*) as total FROM oblgaz_emails")
                    total = cursor.fetchone()[0]
                    
                    self.db_status_var.set(f"БД: {total} записей")
                    self.log_message(f"БД: Таблица есть, записей: {total}")
                else:
                    self.db_status_var.set("БД: Нет таблицы")
                    self.log_message("БД: Таблица не найдена")
                
            except Exception as e:
                self.db_status_var.set("БД: Ошибка")
                self.log_message(f"БД ошибка: {e}")
            finally:
                conn.close()
        else:
            self.db_status_var.set("БД: Нет подключения")
            self.log_message("Не удалось подключиться к БД")
    
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
            saved_count = 0
            
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
                        
                        # Сохраняем в БД
                        if save_email_to_db(email_data):
                            saved_count += 1
                        
                        # Отображаем в интерфейсе
                        self.display_email(email_data, i + 1)
                        
                except Exception as e:
                    self.log_message(f"Ошибка обработки письма {email_id}: {e}")
            
            # Итоги
            self.log_message("=" * 60)
            self.log_message(f"ОБРАБОТКА ЗАВЕРШЕНА")
            self.log_message(f"Обработано: {emails_to_process} писем")
            self.log_message(f"Сохранено в БД: {saved_count}")
            
            self.emails_area.insert(tk.END, f"\n{'═'*60}\n")
            self.emails_area.insert(tk.END, f"ИТОГИ ОБРАБОТКИ\n")
            self.emails_area.insert(tk.END, f"• Обработано писем: {emails_to_process}\n")
            self.emails_area.insert(tk.END, f"• Сохранено в БД: {saved_count}\n")
            self.emails_area.insert(tk.END, f"• Отправитель: {TARGET_SENDER}\n")
            self.emails_area.insert(tk.END, f"• Период: последние {days} дней\n")
            self.emails_area.insert(tk.END, f"• Папка: {folder}\n")
            
            self.status_var.set(f"Готово. Сохранено: {saved_count}")
            
            # Закрываем соединение
            mail.close()
            mail.logout()
            self.log_message("Соединение закрыто")
            
            # Обновляем статистику
            self.update_stats()
            
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
    
    def update_stats(self):
        """Обновляет статистику"""
        conn = get_sql_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN has_attachment = 1 THEN 1 ELSE 0 END) as with_attachments,
                    COUNT(DISTINCT sender_email) as unique_senders,
                    MIN(fetched_date) as first_fetch,
                    MAX(fetched_date) as last_fetch
                FROM oblgaz_emails
            """)
            
            stats = cursor.fetchone()
            
            # Статистика по отправителям
            cursor.execute("""
                SELECT 
                    sender_email,
                    COUNT(*) as email_count,
                    MAX(date_received) as last_email
                FROM oblgaz_emails
                WHERE sender_email IS NOT NULL
                GROUP BY sender_email
                ORDER BY email_count DESC
                LIMIT 10
            """)
            
            top_senders = cursor.fetchall()
            
            # Статистика по дням
            cursor.execute("""
                SELECT 
                    CAST(fetched_date AS DATE) as fetch_date,
                    COUNT(*) as daily_count
                FROM oblgaz_emails
                GROUP BY CAST(fetched_date AS DATE)
                ORDER BY fetch_date DESC
                LIMIT 7
            """)
            
            daily_stats = cursor.fetchall()
            
            # Обновляем статус
            self.total_emails_var.set(f"Всего: {stats[0] if stats[0] else 0}")
            
            # Обновляем область статистики
            self.stats_area.delete(1.0, tk.END)
            
            self.stats_area.insert(tk.END, "СТАТИСТИКА ПОЧТЫ OBLGAZ\n")
            self.stats_area.insert(tk.END, "=" * 50 + "\n\n")
            
            # Общая статистика
            self.stats_area.insert(tk.END, "ОБЩАЯ СТАТИСТИКА:\n")
            self.stats_area.insert(tk.END, f"• Всего писем: {stats[0] if stats[0] else 0}\n")
            self.stats_area.insert(tk.END, f"• С вложениями: {stats[1] if stats[1] else 0}\n")
            self.stats_area.insert(tk.END, f"• Уникальных отправителей: {stats[2] if stats[2] else 0}\n")
            self.stats_area.insert(tk.END, f"• Первая загрузка: {stats[3] if stats[3] else 'Н/Д'}\n")
            self.stats_area.insert(tk.END, f"• Последняя загрузка: {stats[4] if stats[4] else 'Н/Д'}\n\n")
            
            # Топ отправителей
            self.stats_area.insert(tk.END, "ТОП ОТПРАВИТЕЛЕЙ:\n")
            for sender, count, last_date in top_senders:
                self.stats_area.insert(tk.END, f"• {sender}: {count} писем, последнее: {last_date}\n")
            
            self.stats_area.insert(tk.END, "\n")
            
            # Ежедневная статистика
            self.stats_area.insert(tk.END, "ПОСЛЕДНИЕ 7 ДНЕЙ:\n")
            for date, count in daily_stats:
                self.stats_area.insert(tk.END, f"• {date}: {count} писем\n")
            
            self.log_message("Статистика обновлена")
            
        except Exception as e:
            self.log_message(f"Ошибка обновления статистики: {e}")
        finally:
            conn.close()
    
    def clear_logs(self):
        """Очищает логи"""
        self.logs_area.delete(1.0, tk.END)
        self.log_message("Логи очищены")
    
    def export_to_csv(self):
        """Экспортирует данные в CSV"""
        conn = get_sql_connection()
        if not conn:
            messagebox.showerror("Ошибка", "Нет подключения к БД")
            return
        
        try:
            cursor = conn.cursor(as_dict=True)
            
            cursor.execute("""
                SELECT 
                    sender_email,
                    sender_name,
                    subject,
                    date_received,
                    LEFT(body_text, 500) as preview,
                    has_attachment,
                    attachment_count,
                    importance,
                    folder,
                    fetched_date
                FROM oblgaz_emails
                ORDER BY date_received DESC
            """)
            
            rows = cursor.fetchall()
            
            if not rows:
                messagebox.showinfo("Информация", "Нет данных для экспорта")
                return
            
            # Создаем файл в домашней директории
            home_dir = os.path.expanduser("~")
            filename = os.path.join(home_dir, f"oblgaz_emails_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            
            with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                # Заголовок
                f.write("Email отправителя;Имя отправителя;Тема;Дата письма;Превью;Вложение;Кол-во вложений;Важность;Папка;Дата загрузки\n")
                
                # Данные
                for row in rows:
                    # Экранируем кавычки
                    escape = lambda x: str(x).replace('"', '""').replace(';', ',') if x else ''
                    
                    line = (f'"{escape(row["sender_email"])}";'
                           f'"{escape(row["sender_name"])}";'
                           f'"{escape(row["subject"])}";'
                           f'"{escape(row["date_received"])}";'
                           f'"{escape(row["preview"])}";'
                           f'"{("Да" if row["has_attachment"] else "Нет")}";'
                           f'"{row["attachment_count"]}";'
                           f'"{escape(row["importance"])}";'
                           f'"{escape(row["folder"])}";'
                           f'"{escape(row["fetched_date"])}"\n')
                    f.write(line)
            
            self.log_message(f"Экспортировано в: {filename}")
            self.log_message(f"Записей: {len(rows)}")
            
            # Показываем диалог
            messagebox.showinfo("Экспорт завершен", 
                              f"Данные экспортированы!\n\n"
                              f"Файл: {filename}\n"
                              f"Записей: {len(rows)}")
            
        except Exception as e:
            self.log_message(f"Ошибка экспорта: {e}")
            messagebox.showerror("Ошибка", f"Ошибка экспорта:\n{str(e)}")
        finally:
            conn.close()
    
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