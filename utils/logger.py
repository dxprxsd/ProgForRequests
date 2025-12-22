# utils/logger.py - Система логирования
import tkinter as tk
from datetime import datetime

class Logger:
    def __init__(self, text_widget=None):
        self.text_widget = text_widget
        
    def log(self, message, level="INFO"):
        """Добавляет сообщение в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Выводим в консоль
        print(log_entry)
        
        # Если есть текстовый виджет, добавляем туда
        if self.text_widget:
            try:
                # Настраиваем цвет в зависимости от уровня
                if level == "ERROR":
                    color = "#ff4444"
                elif level == "WARNING":
                    color = "#ffaa00"
                elif level == "SUCCESS":
                    color = "#44ff44"
                else:
                    color = "#ffffff"
                
                # Вставляем текст с цветом
                self.text_widget.insert(tk.END, log_entry + "\n")
                
                # Применяем цвет к последней строке
                start_index = self.text_widget.index("end-2l")
                end_index = self.text_widget.index("end-1c")
                
                # Создаем уникальный тег для каждой строки
                tag_name = f"color_{level}_{timestamp.replace(':', '_')}"
                self.text_widget.tag_add(tag_name, start_index, end_index)
                self.text_widget.tag_config(tag_name, foreground=color)
                
                self.text_widget.see(tk.END)
            except Exception as e:
                print(f"Ошибка записи в лог-виджет: {e}")
    
    def set_text_widget(self, text_widget):
        """Устанавливает текстовый виджет для вывода логов"""
        self.text_widget = text_widget
    
    def clear(self):
        """Очищает логи"""
        if self.text_widget:
            try:
                self.text_widget.delete(1.0, tk.END)
            except:
                pass
        print("Логи очищены")