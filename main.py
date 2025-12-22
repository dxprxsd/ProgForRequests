#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# main.py - Главный файл запуска приложения

import sys
import os
import tkinter as tk
from tkinter import messagebox
import platform

# Добавляем текущую директорию в путь для импорта модулей
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
        print(f"Не хватает пакетов: {', '.join(missing_packages)}")
        
        if platform.system().lower() == 'linux':
            print("\nУстановка для RedOS/CentOS/RHEL:")
            print("  sudo yum install python3-devel gcc freetds-devel")
            print(f"  sudo pip3 install {' '.join(missing_packages)}")
        
        return False
    
    return True

def main():
    """Основная функция запуска приложения"""
    print("\n" + "="*70)
    print("OBLGAZ EMAIL FETCHER ДЛЯ REDOS/LINUX")
    print("="*70)
    
    # Проверяем зависимости
    if not check_dependencies():
        print("\nУстановите зависимости и перезапустите программу")
        sys.exit(1)
    
    print("✓ Зависимости проверены")
    
    # Проверяем DISPLAY для GUI
    if 'DISPLAY' not in os.environ:
        print("Переменная DISPLAY не установлена")
        os.environ['DISPLAY'] = ':0'
        print("   Установлено DISPLAY=:0")
    
    try:
        # Импортируем здесь, чтобы ошибки импорта были обработаны
        from ui.main_window import MainWindow
        from proxy_manager import ProxyManager
        
        # Настраиваем прокси
        print("\nНастройка прокси...")
        proxy_manager = ProxyManager()
        proxy_status = proxy_manager.setup_mail_proxy()
        
        if not proxy_status:
            print("Прокси не настроен, некоторые функции могут не работать")
        
        # Создаем главное окно
        print("Запуск графического интерфейса...")
        root = tk.Tk()
        
        # Создаем приложение
        app = MainWindow(root)
        
        # Запускаем главный цикл
        print("\n" + "="*70)
        print("Приложение запущено успешно!")
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