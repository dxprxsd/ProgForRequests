# main.py - с выбором режима
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import tkinter as tk
from tkinter import messagebox, simpledialog
import platform

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_dependencies():
    """Проверяет необходимые зависимости"""
    missing_packages = []
    
    try:
        import pymssql
    except ImportError:
        missing_packages.append("pymssql")
    
    try:
        import socks
    except ImportError:
        missing_packages.append("pysocks")
    
    if missing_packages:
        print(f"\nНе хватает пакетов: {', '.join(missing_packages)}")
        
        if platform.system().lower() == 'linux':
            print("\nДля RedOS/CentOS/RHEL выполните:")
            print("  sudo yum install python3-devel gcc freetds-devel")
            
            install_now = input("\nУстановить pysocks? (y/n): ")
            if install_now.lower() == 'y':
                os.system("sudo pip3 install pysocks")
                print("pysocks установлен")
    
    return True

def check_email_credentials():
    """Проверяет учетные данные почты"""
    from config import Config
    
    print("\n" + "="*70)
    print("ПРОВЕРКА УЧЕТНЫХ ДАННЫХ ПОЧТЫ")
    print("="*70)
    
    print(f"\nТекущие настройки:")
    print(f"  Сервер: {Config.MAIL_SERVER}")
    print(f"  Пользователь: {Config.USERNAME}")
    print(f"  Пароль: {'*' * len(Config.PASSWORD)}")
    
    # Спросим пользователя о режиме
    print("\n" + "-"*70)
    print("Выберите режим работы:")
    print("  1. Реальный режим (попробовать подключиться к почте)")
    print("  2. Тестовый режим (использовать тестовые данные)")
    print("  3. Проверить подключение сейчас")
    
    choice = input("\nВаш выбор (1/2/3): ").strip()
    
    if choice == '3':
        # Тестируем подключение
        from mail_client import MailClient
        from utils.logger import Logger
        
        logger = Logger()
        client = MailClient(logger)
        client.test_mode = False  # Реальный режим
        
        print("\nТестирую подключение...")
        if client.connect():
            print("✓ Подключение успешно!")
            
            # Пробуем получить папки
            try:
                import ssl
                import imaplib
                
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                imap = imaplib.IMAP4_SSL(
                    host=Config.MAIL_SERVER,
                    port=Config.IMAP_PORT,
                    ssl_context=ssl_context
                )
                
                imap.login(Config.USERNAME, Config.PASSWORD)
                status, folders = imap.list()
                
                if status == 'OK':
                    print(f"✓ Найдено папок: {len(folders)}")
                    for folder in folders[:5]:
                        print(f"  - {folder.decode('utf-8', errors='ignore')[:50]}")
                
                imap.logout()
                
            except Exception as e:
                print(f"✗ Ошибка: {e}")
            
            client.disconnect()
            
            # Спросим продолжить
            continue_real = input("\nПродолжить в реальном режиме? (y/n): ").lower()
            if continue_real == 'y':
                return True
            else:
                return False
        else:
            print("✗ Не удалось подключиться")
            use_test = input("\nИспользовать тестовый режим? (y/n): ").lower()
            return use_test == 'y'
    
    elif choice == '1':
        return True  # Реальный режим
    elif choice == '2':
        return False  # Тестовый режим
    else:
        print("Использую тестовый режим по умолчанию")
        return False

def main():
    """Основная функция запуска приложения"""
    print("\n" + "="*70)
    print("OBLGAZ EMAIL FETCHER")
    print("="*70)
    
    # Проверяем зависимости
    if not check_dependencies():
        print("\nУстановите зависимости и перезапустите программу")
        sys.exit(1)
    
    # Проверяем учетные данные
    use_real_mode = check_email_credentials()
    
    if use_real_mode:
        print("\n" + "="*70)
        print("РЕАЛЬНЫЙ РЕЖИМ АКТИВИРОВАН")
        print("Программа попытается подключиться к реальной почте")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("ТЕСТОВЫЙ РЕЖИМ АКТИВИРОВАН")
        print("Программа будет использовать тестовые данные")
        print("="*70)
    
    # Настраиваем окружение
    if 'DISPLAY' not in os.environ:
        print("\nПеременная DISPLAY не установлена")
        os.environ['DISPLAY'] = ':0'
        print("  Установлено DISPLAY=:0")
    
    try:
        # Импортируем и настраиваем
        from ui.main_window import MainWindow
        from mail_client import MailClient
        from config import Config
        
        # Устанавливаем режим в конфиге
        Config.TEST_MODE = not use_real_mode
        
        # Создаем главное окно
        print("\nЗапуск графического интерфейса...")
        root = tk.Tk()
        
        # Создаем приложение
        app = MainWindow(root)
        
        # Запускаем главный цикл
        print("\n" + "="*70)
        print("Приложение запущено успешно!")
        
        if use_real_mode:
            print("РАБОТАЕТ В РЕАЛЬНОМ РЕЖИМЕ")
        else:
            print("РАБОТАЕТ В ТЕСТОВОМ РЕЖИМЕ")
            
        print("="*70)
        
        root.mainloop()
        
    except ImportError as e:
        print(f"\nОшибка импорта модуля: {e}")
        print("\nУбедитесь, что все файлы находятся в правильных директориях:")
        print("  ui/main_window.py")
        print("  ui/db_work_window.py")
        print("  proxy_manager.py")
        print("  mail_client.py")
        print("  database_client.py")
        print("  utils/logger.py")
        print("  utils/helpers.py")
        sys.exit(1)
        
    except tk.TclError as e:
        if "display" in str(e).lower():
            print(f"\nОшибка GUI: {e}")
            print("\nРешения:")
            print("  1. Запустите на машине с GUI")
            print("  2. Или используйте ssh -X для удаленного доступа")
            print("  3. Установите X11 forwarding")
            print("\nДля запуска без GUI используйте:")
            print("  export DISPLAY=:0")
        else:
            print(f"\nОшибка Tkinter: {e}")
        sys.exit(1)
        
    except Exception as e:
        print(f"\nНеожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()