# mail_client.py - Клиент для работы с почтой
import imaplib
import smtplib
import socket
import ssl
import time
import email
import re
from datetime import datetime, timedelta
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import Config
from utils.logger import Logger
from utils.helpers import parse_email_date, decode_email_header, extract_email_from_string

class MailClient:
    def __init__(self, logger=None):
        self.logger = logger or Logger()
        self.connection = None
        self.connected = False
    
    def connect(self):
        """Подключается к IMAP серверу"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                self.logger.log(f"Попытка подключения {attempt + 1}/{max_retries}...")
                
                # Создаем SSL контекст
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # Создаем подключение
                self.connection = imaplib.IMAP4_SSL(
                    host=Config.MAIL_SERVER,
                    port=Config.IMAP_PORT,
                    ssl_context=ssl_context
                )
                
                # Устанавливаем таймаут
                self.connection.sock.settimeout(45.0)
                
                # Логинимся
                self.connection.login(Config.USERNAME, Config.PASSWORD)
                
                self.connected = True
                self.logger.log(f"Успешное подключение к {Config.MAIL_SERVER}:{Config.IMAP_PORT}", "SUCCESS")
                return True
                
            except socket.timeout:
                self.logger.log(f"Таймаут подключения (попытка {attempt + 1})", "WARNING")
                if attempt < max_retries - 1:
                    time.sleep(3)
            except ssl.SSLError as e:
                self.logger.log(f"SSL ошибка: {e}", "WARNING")
                if attempt < max_retries - 1:
                    time.sleep(3)
            except Exception as e:
                self.logger.log(f"Ошибка подключения: {e}", "ERROR")
                if attempt < max_retries - 1:
                    time.sleep(3)
        
        self.connected = False
        return False
    
    def disconnect(self):
        """Отключается от сервера"""
        if self.connection and self.connected:
            try:
                self.connection.logout()
                self.connected = False
                self.logger.log("Отключение от почтового сервера", "INFO")
            except:
                pass
    
    def get_folders(self):
        """Получает список папок"""
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            status, folders = self.connection.list()
            if status == 'OK':
                folder_list = []
                for folder in folders:
                    try:
                        folder_str = folder.decode('utf-8', errors='ignore')
                        # Извлекаем имя папки
                        match = re.search(r'\"([^\"]+)\"$', folder_str)
                        if match:
                            folder_list.append(match.group(1))
                        else:
                            # Альтернативный способ извлечения
                            parts = folder_str.split('"')
                            if len(parts) >= 2:
                                folder_list.append(parts[-2])
                    except:
                        continue
                
                return folder_list
            else:
                self.logger.log("Не удалось получить список папок", "ERROR")
                return []
        except Exception as e:
            self.logger.log(f"Ошибка получения папок: {e}", "ERROR")
            return []
    
    def search_emails(self, folder='INBOX', days=30, sender=None, limit=50):
        """Ищет письма по критериям"""
        if not self.connected:
            if not self.connect():
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
    
    def send_email(self, to_email, subject, body, cc=None, bcc=None, attachments=None):
        """Отправляет email"""
        try:
            # Создаем сообщение
            msg = MIMEMultipart()
            msg['From'] = Config.USERNAME
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = cc
            
            # Добавляем тело письма
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # TODO: Добавить обработку вложений
            
            # Подключаемся к SMTP
            smtp_conn = smtplib.SMTP(
                host=Config.MAIL_SERVER,
                port=Config.SMTP_PORT,
                timeout=30
            )
            
            # Приветствие и шифрование
            smtp_conn.ehlo()
            smtp_conn.starttls()
            smtp_conn.ehlo()
            
            # Аутентификация
            smtp_conn.login(Config.USERNAME, Config.PASSWORD)
            
            # Отправляем
            recipients = [to_email]
            if cc:
                recipients.extend([addr.strip() for addr in cc.split(',')])
            if bcc:
                recipients.extend([addr.strip() for addr in bcc.split(',')])
            
            smtp_conn.send_message(msg, from_addr=Config.USERNAME, to_addrs=recipients)
            smtp_conn.quit()
            
            self.logger.log(f"Письмо отправлено на {to_email}", "SUCCESS")
            return True
            
        except Exception as e:
            self.logger.log(f"Ошибка отправки письма: {e}", "ERROR")
            return False
    
    def test_connection(self):
        """Тестирует подключение к почтовому серверу"""
        self.logger.log("Тестирование подключения к почте...", "INFO")
        
        try:
            # Тест IMAP
            if not self.connect():
                return False
            
            # Тест получения папок
            folders = self.get_folders()
            self.logger.log(f"Почта подключена. Папок: {len(folders)}", "SUCCESS")
            
            if folders:
                self.logger.log(f"Первые папки: {', '.join(folders[:3])}", "INFO")
            
            self.disconnect()
            return True
            
        except Exception as e:
            self.logger.log(f"Ошибка теста почты: {e}", "ERROR")
            return False