# test_login.py
#!/usr/bin/env python3
import ssl
import imaplib

server = 'mail.oblgaz.nnov.ru'
port = 993

# Пробуем разные варианты
test_cases = [
    ('kuzminiv@oblgaz.nnov.ru', 'sup800'),
    ('kuzminiv', 'sup800'),
    ('kuzminiv@mail.oblgaz.nnov.ru', 'sup800'),
    ('lk.oblgaznnov.ru', 'sup800'),
    ('support_lk@oblgaz.nnov.ru', 'sup800')
]

context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

for username, password in test_cases:
    try:
        print(f"\nПробую: {username}")
        imap = imaplib.IMAP4_SSL(server, port, ssl_context=context)
        imap.login(username, password)
        print(f"УСПЕХ!")
        
        # Получаем папки
        status, folders = imap.list()
        if status == 'OK':
            print(f"Папок: {len(folders)}")
            for folder in folders[:3]:
                print(f"    - {folder.decode('utf-8', errors='ignore')[:50]}")
        
        imap.logout()
        print(f"\n РЕКОМЕНДУЮ ИСПОЛЬЗОВАТЬ: {username}")
        break
        
    except Exception as e:
        print(f"Ошибка: {str(e)[:100]}")