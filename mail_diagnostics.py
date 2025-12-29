# mail_diagnostics.py
#!/usr/bin/env python3
"""
Утилита для диагностики почтового подключения
Запуск: python mail_diagnostics.py
"""

import sys
import os
import socket
import subprocess

# Добавляем путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config

def test_network_connectivity():
    """Тестирует сетевое подключение"""
    print("\n" + "="*80)
    print("ТЕСТ СЕТЕВОГО ПОДКЛЮЧЕНИЯ")
    print("="*80)
    
    tests = [
        ("Проверка DNS", f"nslookup {Config.MAIL_SERVER}"),
        ("Проверка ping", f"ping -c 3 {Config.MAIL_SERVER}"),
        ("Проверка IMAP порта (993)", f"nc -zv {Config.MAIL_SERVER} 993"),
        ("Проверка IMAP без SSL (143)", f"nc -zv {Config.MAIL_SERVER} 143"),
        ("Проверка POP3 SSL (995)", f"nc -zv {Config.MAIL_SERVER} 995"),
        ("Проверка SMTP (587)", f"nc -zv {Config.MAIL_SERVER} 587"),
        ("Проверка прокси", f"nc -zv {Config.PROXY_HOST} {Config.PROXY_PORT}"),
    ]
    
    for test_name, command in tests:
        print(f"\n{test_name}:")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"  ✓ Успешно")
                if "nslookup" in command:
                    for line in result.stdout.split('\n'):
                        if 'Address:' in line:
                            print(f"    {line.strip()}")
            else:
                print(f"  ✗ Ошибка")
                print(f"    {result.stderr[:100] if result.stderr else result.stdout[:100]}")
                
        except subprocess.TimeoutExpired:
            print(f"  ✗ Таймаут")
        except Exception as e:
            print(f"  ✗ Исключение: {e}")

def test_python_connection():
    """Тестирует подключение через Python"""
    print("\n" + "="*80)
    print("ТЕСТ ПОДКЛЮЧЕНИЯ ЧЕРЕЗ PYTHON")
    print("="*80)
    
    try:
        import ssl
        import imaplib
        
        print("\n1. Тест SSL сертификата...")
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            sock = socket.create_connection((Config.MAIL_SERVER, 993), timeout=10)
            ssl_sock = ssl_context.wrap_socket(sock, server_hostname=Config.MAIL_SERVER)
            ssl_sock.close()
            print(f"  ✓ SSL подключение к {Config.MAIL_SERVER}:993 возможно")
        except Exception as e:
            print(f"  ✗ SSL ошибка: {e}")
        
        print("\n2. Тест IMAP логина...")
        try:
            from mail_client import MailClient
            from utils.logger import Logger
            
            logger = Logger()
            client = MailClient(logger)
            
            if client.connect():
                print(f"  ✓ IMAP подключение и логин успешны")
                
                # Получаем папки
                folders = client.get_folders()
                if folders:
                    print(f"    Папок найдено: {len(folders)}")
                    print(f"    Примеры: {', '.join(folders[:3])}")
                
                client.disconnect()
            else:
                print(f"  ✗ IMAP подключение не удалось")
                
        except ImportError as e:
            print(f"  ✗ Ошибка импорта: {e}")
        except Exception as e:
            print(f"  ✗ Исключение: {e}")
            
    except Exception as e:
        print(f"Ошибка теста Python: {e}")

def check_configuration():
    """Проверяет конфигурацию"""
    print("\n" + "="*80)
    print("ПРОВЕРКА КОНФИГУРАЦИИ")
    print("="*80)
    
    config_info = [
        ("Почтовый сервер", Config.MAIL_SERVER),
        ("Пользователь", Config.USERNAME),
        ("IMAP порт", Config.IMAP_PORT),
        ("Прокси хост", Config.PROXY_HOST),
        ("Прокси порт", Config.PROXY_PORT),
        ("SQL сервер", Config.SQL_SERVER),
        ("Целевой отправитель", Config.TARGET_SENDER),
    ]
    
    for key, value in config_info:
        print(f"{key:20}: {value}")
    
    # Проверка паролей
    print(f"\nПароль почты: {'установлен' if Config.PASSWORD else 'не установлен'}")
    print(f"Пароль SQL: {'установлен' if Config.SQL_PASSWORD else 'не установлен'}")
    print(f"Пароль прокси: {'установлен' if Config.PROXY_PASS else 'не установлен'}")

def main():
    """Основная функция"""
    print("\n" + "="*80)
    print("ДИАГНОСТИКА ПОЧТОВОГО ПОДКЛЮЧЕНИЯ")
    print("="*80)
    
    check_configuration()
    test_network_connectivity()
    test_python_connection()
    
    print("\n" + "="*80)
    print("РЕКОМЕНДАЦИИ:")
    print("="*80)
    print("1. Проверьте правильность логина/пароля")
    print("2. Убедитесь что почтовый сервер доступен из вашей сети")
    print("3. Попробуйте подключиться без прокси")
    print("4. Проверьте настройки брандмауэра")
    print("5. Для теста используйте команду:")
    print(f"   openssl s_client -connect {Config.MAIL_SERVER}:993 -crlf")
    print("\nЕсли ничего не помогает:")
    print("1. Используйте веб-интерфейс: https://{Config.MAIL_SERVER}")
    print("2. Обратитесь к системному администратору")

if __name__ == "__main__":
    main()