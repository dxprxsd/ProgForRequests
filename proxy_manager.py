# proxy_manager.py - Менеджер прокси-соединений
import socks
import socket
import os
import urllib.request

from config import Config

class ProxyManager:
    def __init__(self):
        self.proxy_status = False
        
    def setup_mail_proxy(self):
        """Настраиваем прокси для почтовых соединений"""
        try:
            # Сохраняем оригинальные функции
            original_socket = socket.socket
            original_create_connection = socket.create_connection
            
            def create_proxy_socket(family=socket.AF_INET, type=socket.SOCK_STREAM, 
                                    proto=0, fileno=None):
                """Создает сокет с настройкой прокси"""
                if fileno is None:
                    sock = socks.socksocket(family=family, type=type, proto=proto)
                    sock.set_proxy(
                        socks.SOCKS5,
                        Config.PROXY_HOST,
                        Config.PROXY_PORT,
                        username=Config.PROXY_USER,
                        password=Config.PROXY_PASS,
                        rdns=True
                    )
                    return sock
                return original_socket(family, type, proto, fileno)
            
            # Патчим socket для использования прокси
            socket.socket = create_proxy_socket
            
            def patched_create_connection(address, timeout=None, source_address=None):
                """Патчим create_connection для работы с прокси"""
                host, port = address
                
                # Принудительно используем IPv4 для обхода проблем
                addrinfo = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
                
                for family, socktype, proto, canonname, sockaddr in addrinfo:
                    sock = None
                    try:
                        sock = create_proxy_socket(family, socktype, proto)
                        
                        if timeout is not None:
                            sock.settimeout(timeout)
                        
                        if source_address:
                            sock.bind(source_address)
                        
                        sock.connect(sockaddr)
                        return sock
                        
                    except Exception:
                        if sock is not None:
                            sock.close()
                        continue
                
                raise OSError(f"Не удалось подключиться к {host}:{port}")
            
            socket.create_connection = patched_create_connection
            
            # Настраиваем переменные окружения
            os.environ['HTTP_PROXY'] = f"http://{Config.PROXY_USER}:{Config.PROXY_PASS}@{Config.PROXY_HOST}:{Config.PROXY_PORT}"
            os.environ['HTTPS_PROXY'] = f"http://{Config.PROXY_USER}:{Config.PROXY_PASS}@{Config.PROXY_HOST}:{Config.PROXY_PORT}"
            os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
            
            print(f"Прокси настроен: {Config.PROXY_HOST}:{Config.PROXY_PORT}")
            self.proxy_status = True
            return True
            
        except Exception as e:
            print(f"Ошибка настройки прокси: {e}")
            self.proxy_status = False
            return False
    
    def test_proxy_connection(self):
        """Тестирует подключение через прокси"""
        try:
            proxy_handler = urllib.request.ProxyHandler({
                'http': f'http://{Config.PROXY_USER}:{Config.PROXY_PASS}@{Config.PROXY_HOST}:{Config.PROXY_PORT}',
                'https': f'http://{Config.PROXY_USER}:{Config.PROXY_PASS}@{Config.PROXY_HOST}:{Config.PROXY_PORT}'
            })
            
            opener = urllib.request.build_opener(proxy_handler)
            response = opener.open('http://httpbin.org/ip', timeout=10)
            ip_info = response.read().decode()
            
            print(f"Прокси работает: {ip_info[:50]}...")
            return True
            
        except Exception as e:
            print(f"Прокси не работает: {e}")
            return False
    
    def get_status(self):
        """Возвращает статус прокси"""
        return self.proxy_status