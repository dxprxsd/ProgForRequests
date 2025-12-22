# utils/helpers.py - Вспомогательные функции
import re
from datetime import datetime
from email.header import decode_header

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

def decode_email_header(header):
    """Декодирует заголовок email"""
    if not header:
        return ""
    
    try:
        decoded_parts = decode_header(header)
        decoded_str = ""
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    decoded_str += part.decode(encoding, errors='ignore')
                else:
                    decoded_str += part.decode('utf-8', errors='ignore')
            else:
                decoded_str += str(part)
        
        return decoded_str.strip()
    except:
        return str(header) if header else ""

def extract_email_from_string(email_string):
    """Извлекает email адрес из строки"""
    if not email_string:
        return ""
    
    # Поиск email в строке
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    match = re.search(email_pattern, email_string)
    
    if match:
        return match.group(0)
    
    return email_string

def validate_email(email):
    """Проверяет валидность email адреса"""
    if not email:
        return False
    
    email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(email_pattern, email) is not None

def truncate_text(text, max_length=100):
    """Обрезает текст до указанной длины"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."