# webmail_client.py
import requests
import re
import json
from config import Config
from utils.logger import Logger

class WebMailClient:
    """Клиент для работы с почтой через веб-интерфейс (без BeautifulSoup)"""
    
    def __init__(self, logger=None):
        self.logger = logger or Logger()
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.logged_in = False
        self.base_url = f"https://{Config.MAIL_SERVER}"
        
    def simple_login(self):
        """Простая попытка логина без парсинга HTML"""
        try:
            self.logger.log("Попытка простого входа...", "INFO")
            
            # Пробуем стандартные пути для разных почтовых систем
            login_endpoints = [
                "/owa/auth.owa",  # Exchange
                "/roundcube/",    # Roundcube
                "/webmail/",      # Generic webmail
                "/mail/",         # Generic mail
                "/"               # Root
            ]
            
            for endpoint in login_endpoints:
                try:
                    url = self.base_url + endpoint
                    response = self.session.get(url, timeout=10)
                    
                    # Проверяем тип почтовой системы
                    if 'owa' in endpoint.lower() and 'Exchange' in response.text:
                        self.logger.log("Обнаружен Exchange OWA", "INFO")
                        return self._try_exchange_login()
                    elif 'roundcube' in response.text.lower():
                        self.logger.log("Обнаружен Roundcube", "INFO")
                        return self._try_roundcube_login()
                    elif 'squirrelmail' in response.text.lower():
                        self.logger.log("Обнаружен SquirrelMail", "INFO")
                        return self._try_squirrelmail_login()
                    
                except Exception as e:
                    self.logger.log(f"Ошибка проверки {endpoint}: {e}", "WARNING")
                    continue
            
            self.logger.log("Не удалось определить тип почтовой системы", "ERROR")
            return False
            
        except Exception as e:
            self.logger.log(f"Ошибка простого логина: {e}", "ERROR")
            return False
    
    def _try_exchange_login(self):
        """Попытка логина в Exchange OWA"""
        try:
            # OWA часто использует форму на /owa/auth.owa
            login_url = f"{self.base_url}/owa/auth.owa"
            
            # Пробуем разные комбинации полей
            login_payloads = [
                {'username': Config.USERNAME, 'password': Config.PASSWORD},
                {'destination': 'https://mail.oblgaz.nnov.ru/owa/', 
                 'flags': '0', 
                 'username': Config.USERNAME, 
                 'password': Config.PASSWORD},
                {'username': Config.USERNAME.split('@')[0],  # Без домена
                 'password': Config.PASSWORD}
            ]
            
            for payload in login_payloads:
                try:
                    response = self.session.post(login_url, data=payload, timeout=10)
                    
                    # Проверяем успешность по URL или тексту
                    if 'inbox' in response.url.lower() or 'logout' in response.text.lower():
                        self.logged_in = True
                        self.logger.log("Успешный вход в Exchange OWA", "SUCCESS")
                        return True
                except Exception as e:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.log(f"Ошибка Exchange логина: {e}", "ERROR")
            return False
    
    def _try_roundcube_login(self):
        """Попытка логина в Roundcube"""
        try:
            login_url = f"{self.base_url}/roundcube/"
            
            # Roundcube стандартные поля
            payload = {
                '_user': Config.USERNAME,
                '_pass': Config.PASSWORD,
                '_task': 'login',
                '_action': 'login'
            }
            
            response = self.session.post(login_url, data=payload, timeout=10)
            
            if 'mailbox' in response.url or 'inbox' in response.text:
                self.logged_in = True
                self.logger.log("Успешный вход в Roundcube", "SUCCESS")
                return True
            
            return False
            
        except Exception as e:
            self.logger.log(f"Ошибка Roundcube логина: {e}", "ERROR")
            return False
    
    def _try_squirrelmail_login(self):
        """Попытка логина в SquirrelMail"""
        try:
            login_url = f"{self.base_url}/src/redirect.php"
            
            payload = {
                'login_username': Config.USERNAME,
                'secretkey': Config.PASSWORD,
                'js_autodetect_results': '1',
                'just_logged_in': '1'
            }
            
            response = self.session.post(login_url, data=payload, timeout=10)
            
            if 'mailbox' in response.url or 'right_main' in response.text:
                self.logged_in = True
                self.logger.log("Успешный вход в SquirrelMail", "SUCCESS")
                return True
            
            return False
            
        except Exception as e:
            self.logger.log(f"Ошибка SquirrelMail логина: {e}", "ERROR")
            return False
    
    def get_emails_simple(self, limit=10):
        """Простой метод получения писем через HTTP"""
        try:
            if not self.logged_in:
                if not self.simple_login():
                    return self._get_dummy_emails(limit)
            
            # Пробуем разные URL для получения писем
            email_urls = [
                f"{self.base_url}/owa/#path=/mail/inbox",
                f"{self.base_url}/roundcube/?_task=mail&_mbox=INBOX",
                f"{self.base_url}/webmail/src/view_text.php"
            ]
            
            for url in email_urls:
                try:
                    response = self.session.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        # Простой парсинг текста
                        emails = self._parse_emails_from_text(response.text, limit)
                        if emails:
                            self.logger.log(f"Найдено писем: {len(emails)}", "SUCCESS")
                            return emails
                except Exception as e:
                    self.logger.log(f"Ошибка доступа к {url}: {e}", "WARNING")
                    continue
            
            # Если не удалось получить реальные письма
            self.logger.log("Использую тестовые данные", "INFO")
            return self._get_dummy_emails(limit)
            
        except Exception as e:
            self.logger.log(f"Ошибка получения писем: {e}", "ERROR")
            return self._get_dummy_emails(limit)
    
    def _parse_emails_from_text(self, html_text, limit):
        """Простой парсинг email из текста (без BeautifulSoup)"""
        emails = []
        
        try:
            # Ищем email-подобные паттерны в тексте
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            emails_found = re.findall(email_pattern, html_text)
            
            # Ищем строки, которые могут быть темами писем
            lines = html_text.split('\n')
            subject_patterns = [
                r'Subject:\s*(.+)',
                r'Тема:\s*(.+)',
                r'<span[^>]*class=[^>]*subject[^>]*>(.*?)</span>',
                r'<td[^>]*class=[^>]*subject[^>]*>(.*?)</td>'
            ]
            
            subjects = []
            for line in lines:
                for pattern in subject_patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match and match.group(1).strip():
                        subject = match.group(1).strip()
                        subject = re.sub(r'<[^>]+>', '', subject)  # Убираем HTML теги
                        if len(subject) > 3 and subject not in subjects:
                            subjects.append(subject[:100])  # Ограничиваем длину
            
            # Создаем тестовые данные на основе найденной информации
            for i in range(min(limit, max(len(emails_found), len(subjects)))):
                sender = emails_found[i % len(emails_found)] if emails_found else Config.TARGET_SENDER
                subject = subjects[i % len(subjects)] if subjects else f"Письмо #{i+1}"
                
                emails.append({
                    'sender': sender,
                    'subject': subject,
                    'date': f"2024-01-{i+1:02d} 10:00:00",
                    'preview': f"Пример содержимого письма #{i+1}"
                })
            
        except Exception as e:
            self.logger.log(f"Ошибка парсинга: {e}", "WARNING")
        
        return emails
    
    def _get_dummy_emails(self, limit=10):
        """Генерирует тестовые письма"""
        from datetime import datetime, timedelta
        
        emails = []
        now = datetime.now()
        
        for i in range(limit):
            email_date = now - timedelta(days=i)
            
            emails.append({
                'sender': Config.TARGET_SENDER,
                'subject': f'Тестовое письмо #{i+1} от {email_date.strftime("%d.%m.%Y")}',
                'date': email_date.strftime("%Y-%m-%d %H:%M:%S"),
                'preview': f'Это тестовое письмо #{i+1} для демонстрации работы интерфейса. Содержимое генерируется автоматически.'
            })
        
        return emails
    
    def test_connection(self):
        """Тестирует подключение к веб-интерфейсу"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            
            if response.status_code == 200:
                # Определяем тип почтовой системы
                if 'owa' in response.text.lower():
                    mail_type = 'Exchange OWA'
                elif 'roundcube' in response.text.lower():
                    mail_type = 'Roundcube'
                elif 'squirrelmail' in response.text.lower():
                    mail_type = 'Squirrelmail'
                else:
                    mail_type = 'Unknown webmail'
                
                self.logger.log(f"Веб-интерфейс доступен: {mail_type}", "SUCCESS")
                return True
            else:
                self.logger.log(f"Веб-интерфейс недоступен: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.logger.log(f"Ошибка теста веб-интерфейса: {e}", "ERROR")
            return False