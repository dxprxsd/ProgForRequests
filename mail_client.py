# mail_client.py - Исправленная версия с реальным подключением
import imaplib
import smtplib
import socket
import ssl
import time
import email
import re
import sys
from datetime import datetime, timedelta
from email.header import decode_header

from config import Config
from utils.logger import Logger
from utils.helpers import parse_email_date, decode_email_header, extract_email_from_string

class MailClient:
    def __init__(self, logger=None):
        self.logger = logger or Logger()
        self.connection = None
        self.connected = False
        self.test_mode = False  # Флаг тестового режима
    
    def get_dummy_emails(self, days=30, limit=50, sender=None):
        """Генерирует тестовые письма для отладки (ТОЛЬКО если включен test_mode)"""
        if not self.test_mode:
            return []
            
        self.logger.log("Использую тестовые данные (режим отладки)", "WARNING")
        
        emails = []
        now = datetime.now()
        
        for i in range(limit):
            days_ago = (i * days) / limit
            email_date = now - timedelta(days=days_ago)
            sender_email = sender or Config.TARGET_SENDER
            
            email_data = {
                'email_id': f'test_{i}',
                'message_id': f'<test_{i}@oblgaz.nnov.ru>',
                'sender_email': sender_email,
                'sender_name': 'Support LK' if 'support' in sender_email.lower() else 'Тестовый Отправитель',
                'recipient_email': Config.USERNAME,
                'subject': f'Тестовое письмо #{i+1} от {email_date.strftime("%d.%m.%Y")}',
                'date_received': email_date,
                'body_text': f'Это тестовое письмо #{i+1}.\n\n'
                           f'Отправитель: {sender_email}\n'
                           f'Дата: {email_date.strftime("%Y-%m-%d %H:%M")}\n'
                           f'Содержание письма для отладки интерфейса.\n',
                'body_html': '',
                'has_attachment': 1 if i % 3 == 0 else 0,
                'attachment_count': 1 if i % 3 == 0 else 0,
                'importance': 'high' if i % 5 == 0 else 'normal',
                'folder': 'INBOX',
                'is_read': 0
            }
            emails.append(email_data)
        
        return emails
    
    def connect(self):
        """Пытается подключиться к IMAP серверу РЕАЛЬНО"""
        if self.test_mode:
            self.logger.log("Тестовый режим: пропускаю реальное подключение", "INFO")
            return True
            
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                self.logger.log(f"Попытка подключения {attempt + 1}/{max_retries}...")
                
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                self.connection = imaplib.IMAP4_SSL(
                    host=Config.MAIL_SERVER,
                    port=Config.IMAP_PORT,
                    ssl_context=ssl_context
                )
                
                self.connection.sock.settimeout(45.0)
                
                # Пробуем разные варианты логина
                login_success = False
                login_error = None
                
                # Вариант 1: Как есть
                try:
                    self.connection.login(Config.USERNAME, Config.PASSWORD)
                    login_success = True
                    self.logger.log(f"Успешный логин: {Config.USERNAME}", "SUCCESS")
                except imaplib.IMAP4.error as e:
                    login_error = str(e)
                    self.logger.log(f"Логин {Config.USERNAME} не сработал: {str(e)[:100]}", "WARNING")
                
                # Вариант 2: Без домена (если первый не сработал)
                if not login_success and '@' in Config.USERNAME:
                    try:
                        username_no_domain = Config.USERNAME.split('@')[0]
                        self.connection.login(username_no_domain, Config.PASSWORD)
                        login_success = True
                        Config.USERNAME = username_no_domain  # Обновляем конфиг
                        self.logger.log(f"Успешный логин без домена: {username_no_domain}", "SUCCESS")
                    except imaplib.IMAP4.error as e:
                        login_error = str(e)
                        self.logger.log(f"Логин без домена не сработал: {str(e)[:100]}", "WARNING")
                
                if login_success:
                    self.connected = True
                    self.logger.log("Подключение к почте успешно", "SUCCESS")
                    return True
                else:
                    self.logger.log(f"Не удалось войти. Последняя ошибка: {login_error}", "ERROR")
                    raise Exception(f"Authentication failed: {login_error}")
                
            except socket.timeout:
                self.logger.log(f"Таймаут подключения (попытка {attempt + 1})", "WARNING")
            except ssl.SSLError as e:
                self.logger.log(f"SSL ошибка: {e}", "WARNING")
            except Exception as e:
                self.logger.log(f"Ошибка подключения: {e}", "ERROR")
            
            if attempt < max_retries - 1:
                time.sleep(3)
        
        self.connected = False
        self.logger.log("Подключение не удалось после всех попыток", "ERROR")
        return False
    
    def disconnect(self):
        """Отключается от сервера"""
        if self.connection and self.connected and not self.test_mode:
            try:
                self.connection.logout()
                self.connected = False
                self.logger.log("Отключение от почтового сервера", "INFO")
            except:
                pass
    
    def search_emails(self, folder='INBOX', days=30, sender=None, limit=50):
        """Ищет письма по критериям РЕАЛЬНО"""
        if self.test_mode:
            self.logger.log("Тестовый режим: возвращаю тестовые данные", "INFO")
            return self.get_dummy_emails(days, limit, sender)
        
        if not self.connected:
            if not self.connect():
                self.logger.log("Не удалось подключиться к почте", "ERROR")
                return []
        
        try:
            # Выбираем папку
            status = self.connection.select(folder)
            if status[0] != 'OK':
                self.logger.log(f"Не удалось выбрать папку '{folder}'", "WARNING")
                folder = 'INBOX'
                self.connection.select(folder)
            
            # Формируем критерий поиска
            since_date = (datetime.now() - timedelta(days=days)).strftime('%d-%b-%Y')
            search_criteria = f'(SINCE "{since_date}")'
            
            if sender:
                search_criteria = f'(FROM "{sender}" {search_criteria})'
            
            self.logger.log(f"Поиск писем: {search_criteria}")
            
            # Ищем письма
            status, email_ids = self.connection.search(None, search_criteria)
            
            if status != 'OK' or not email_ids[0]:
                self.logger.log("Писем не найдено", "INFO")
                return []
            
            email_ids = email_ids[0].split()
            total_found = len(email_ids)
            
            if total_found > limit:
                email_ids = email_ids[-limit:]  # Берем последние письма
                self.logger.log(f"Ограничение: обработаем {limit} из {total_found} писем", "INFO")
            
            emails = []
            processed = 0
            
            for email_id in email_ids:
                try:
                    email_data = self.fetch_email(email_id)
                    if email_data:
                        emails.append(email_data)
                        processed += 1
                        
                        if processed % 10 == 0:
                            self.logger.log(f"Обработано {processed} писем...")
                    
                except Exception as e:
                    self.logger.log(f"Ошибка обработки письма {email_id}: {e}", "WARNING")
                    continue
            
            self.logger.log(f"Обработано писем: {processed}/{len(email_ids)}", "SUCCESS")
            return emails
            
        except Exception as e:
            self.logger.log(f"Ошибка поиска писем: {e}", "ERROR")
            return []
    
    def fetch_email(self, email_id):
        """Получает одно письмо по ID"""
        if self.test_mode:
            return None
            
        try:
            status, msg_data = self.connection.fetch(email_id, '(RFC822)')
            
            if status != 'OK':
                return None
            
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Обрабатываем письмо
            return self.process_email(msg, email_id.decode())
            
        except Exception as e:
            self.logger.log(f"Ошибка получения письма {email_id}: {e}", "WARNING")
            return None
    
    def process_email(self, msg, email_id):
        """Обрабатывает структуру письма"""
        try:
            # Базовые заголовки
            message_id = msg.get('Message-ID', '')
            subject = decode_email_header(msg.get('Subject', 'Без темы'))
            date_received = parse_email_date(msg.get('Date', ''))
            from_header = msg.get('From', '')
            to_header = msg.get('To', Config.USERNAME)
            
            # Извлекаем информацию об отправителе
            sender_email = extract_email_from_string(from_header)
            sender_name = from_header
            
            if '<' in from_header and '>' in from_header:
                parts = from_header.split('<')
                if len(parts) > 1:
                    sender_name = parts[0].strip(' "\'')
                    sender_email = parts[1].split('>')[0].strip()
            
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
                                charset = part.get_content_charset() or 'utf-8'
                                body_text = payload.decode(charset, errors='ignore')
                        except:
                            pass
                    
                    elif content_type == 'text/html':
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                charset = part.get_content_charset() or 'utf-8'
                                body_html = payload.decode(charset, errors='ignore')
                        except:
                            pass
            else:
                # Простое письмо
                content_type = msg.get_content_type()
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        charset = msg.get_content_charset() or 'utf-8'
                        if content_type == 'text/plain':
                            body_text = payload.decode(charset, errors='ignore')
                        elif content_type == 'text/html':
                            body_html = payload.decode(charset, errors='ignore')
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
                'recipient_email': Config.USERNAME,
                'subject': subject,
                'date_received': date_received,
                'body_text': body_text[:4000] if body_text else '',
                'body_html': body_html[:4000] if body_html else '',
                'has_attachment': 1 if has_attachment else 0,
                'attachment_count': attachment_count,
                'importance': importance,
                'folder': 'INBOX',
                'is_read': 0
            }
            
        except Exception as e:
            self.logger.log(f"Ошибка обработки структуры письма: {e}", "ERROR")
            return None
    
    def test_connection(self):
        """Тестирует подключение к почтовому серверу РЕАЛЬНО"""
        self.logger.log("Тестирование подключения к почте...", "INFO")
        
        if self.test_mode:
            self.logger.log("Тестовый режим: возвращаю успех", "INFO")
            return True
            
        try:
            if not self.connect():
                self.logger.log("Не удалось подключиться к почте", "ERROR")
                return False
            
            # Тест получения папок
            try:
                status, folders = self.connection.list()
                if status == 'OK':
                    folder_count = len(folders)
                    self.logger.log(f"Почта подключена. Папок: {folder_count}", "SUCCESS")
                    
                    if folders:
                        # Показываем первые 3 папки
                        folder_names = []
                        for folder in folders[:3]:
                            try:
                                folder_str = folder.decode('utf-8', errors='ignore')
                                match = re.search(r'\"([^\"]+)\"$', folder_str)
                                if match:
                                    folder_names.append(match.group(1))
                            except:
                                pass
                        
                        if folder_names:
                            self.logger.log(f"Первые папки: {', '.join(folder_names)}", "INFO")
                else:
                    self.logger.log("Не удалось получить список папок", "WARNING")
            except Exception as e:
                self.logger.log(f"Ошибка получения папок: {e}", "WARNING")
            
            self.disconnect()
            return True
            
        except Exception as e:
            self.logger.log(f"Ошибка теста почты: {e}", "ERROR")
            return False