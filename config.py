# config.py - Конфигурация приложения
class Config:
    # Почтовый сервер
    MAIL_SERVER = 'mail.oblgaz.nnov.ru'
    SMTP_PORT = 587
    IMAP_PORT = 993
    USERNAME = 'kuzminiv@oblgaz.nnov.ru'
    PASSWORD = 'sup800'
    
    # Прокси
    PROXY_HOST = '192.168.1.2'
    PROXY_PORT = 8080
    PROXY_USER = 'kuzminiv'
    PROXY_PASS = '12345678Q!'
    
    # SQL Server
    SQL_SERVER = '192.168.1.224'
    SQL_PORT = 1433
    SQL_DATABASE = 'DOG'
    SQL_USERNAME = 'kuzmin'
    SQL_PASSWORD = '76543210'
    
    # Целевой отправитель
    TARGET_SENDER = 'support_lk@oblgaz.nnov.ru'
    
    # Настройки интерфейса
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800
    APP_TITLE = "Oblgaz Email Fetcher"

    # Режимы работы
    TEST_MODE = False 
    DEBUG_MODE = True