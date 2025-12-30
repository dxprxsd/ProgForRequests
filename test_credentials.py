# test_credentials.py
#!/usr/bin/env python3

import ssl
import imaplib
import poplib
from config import Config

def test_credentials():
    print("\n" + "="*80)
    print("ТЕСТ УЧЕТНЫХ ДАННЫХ ПОЧТЫ")
    print("="*80)
    
    print(f"\nКонфигурация:")
    print(f"  Сервер: {Config.MAIL_SERVER}")
    print(f"  Пользователь: {Config.USERNAME}")
    print(f"  Пароль: {'*' * len(Config.PASSWORD)}")
    
    # Варианты логинов для тестирования
    possible_usernames = [
        Config.USERNAME,  # текущий
        'kuzminiv',  # без домена
        'kuzminiv@oblgaz-nnov.ru',  # другой домен
        'kuzminiv@oblgaz.nnov.ru',  # текущий
        'kuzminiv@mail.oblgaz.nnov.ru',  # полный
    ]
    
    # Тест IMAP
    print("\n1. Тестирование IMAP подключение...")
    for username in possible_usernames:
        try:
            print(f"Тестируется: {username}")
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            imap = imaplib.IMAP4_SSL(
                host=Config.MAIL_SERVER,
                port=Config.IMAP_PORT,
                ssl_context=ssl_context
            )
            
            imap.login(username, Config.PASSWORD)
            print(f"Успешно!")
            
            # Проверяем папки
            status, folders = imap.list()
            if status == 'OK':
                print(f"Папок найдено: {len(folders)}")
            
            imap.logout()
            print(f"РЕКОМЕНДУЕТСЯ К ИСПОЛЬЗОВАНИЮ: {username}")
            return username
            
        except imaplib.IMAP4.error as e:
            print(f"Ошибка: {str(e)[:100]}")
        except Exception as e:
            print(f"Другая ошибка: {e}")
    
    # Тест POP3
    print("\n2. Тестирание POP3 подключение...")
    for username in possible_usernames:
        for port in [995, 110]:
            try:
                print(f"Тестируется: {username} порт {port}")
                
                if port == 995:
                    pop = poplib.POP3_SSL(Config.MAIL_SERVER, port, timeout=10)
                else:
                    pop = poplib.POP3(Config.MAIL_SERVER, port, timeout=10)
                
                pop.user(username)
                pop.pass_(Config.PASSWORD)
                
                print(f"Успешно! Писем: {len(pop.list()[1])}")
                pop.quit()
                print(f"РЕКОМЕНДУЕТСЯ К ИСПОЛЬЗОВАНИЮ: {username}")
                return username
                
            except poplib.error_proto as e:
                print(f"Ошибка POP3: {str(e)[:100]}")
            except Exception as e:
                print(f"Другая ошибка: {e}")
    
    print("\n" + "="*80)
    print("РЕКОМЕНДАЦИИ:")
    print("="*80)
    print("1. Убедитесь что пароль правильный")
    print("2. Попробуйте изменить логин на:")
    print("   - kuzminiv (без домена)")
    print("   - kuzminiv@oblgaz-nnov.ru (через дефис)")
    print("   - kuzminiv@mail.oblgaz.nnov.ru")
    print("3. Проверьте учетные данные в веб-интерфейсе:")
    print("   https://mail.oblgaz.nnov.ru")
    print("4. Возможно нужен App Password если включена 2FA")
    
    return None

if __name__ == "__main__":
    test_credentials()