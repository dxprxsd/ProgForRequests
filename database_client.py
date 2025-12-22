# database_client.py - Клиент для работы с базой данных
import pymssql
import re

from config import Config
from utils.logger import Logger

class DatabaseClient:
    def __init__(self, logger=None):
        self.logger = logger or Logger()
        self.connection = None
        self.available_databases = []
        self.current_database = Config.SQL_DATABASE
        
    def connect(self, database=None):
        """Подключается к SQL Server"""
        try:
            db_name = database or self.current_database
            
            self.connection = pymssql.connect(
                server=Config.SQL_SERVER,
                port=Config.SQL_PORT,
                user=Config.SQL_USERNAME,
                password=Config.SQL_PASSWORD,
                database=db_name,
                charset='UTF-8',
                login_timeout=15
            )
            
            self.current_database = db_name
            self.logger.log(f"Подключение к БД '{db_name}' успешно", "SUCCESS")
            return True
            
        except pymssql.OperationalError as e:
            if "database" in str(e).lower():
                self.logger.log(f"База данных '{database}' не найдена", "ERROR")
            else:
                self.logger.log(f"Ошибка подключения к SQL Server: {e}", "ERROR")
            return False
        except Exception as e:
            self.logger.log(f"Ошибка подключения к SQL Server: {e}", "ERROR")
            return False
    
    def disconnect(self):
        """Отключается от базы данных"""
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                self.logger.log("Отключение от БД", "INFO")
            except:
                pass
    
    def search_client_by_email(self, email_address):
        """Ищет клиента в базе по email"""
        if not self.connect():
            return None
        
        try:
            cursor = self.connection.cursor(as_dict=True)
            
            # Проверяем наличие таблицы srv_client_fl
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'srv_client_fl'
            """)
            
            if not cursor.fetchone():
                self.logger.log("Таблица srv_client_fl не найдена", "ERROR")
                return None
            
            # Выполняем SQL запрос для поиска по email
            query = """
            SELECT *
            FROM srv_client_fl
            WHERE email = %s
            """
            
            cursor.execute(query, (email_address,))
            results = cursor.fetchall()
            
            self.logger.log(f"Найдено записей: {len(results)}", "INFO")
            return results
            
        except Exception as e:
            self.logger.log(f"Ошибка поиска клиента: {e}", "ERROR")
            return None
        finally:
            self.disconnect()
    
    def get_client_documents(self, client_id):
        """Получает документы клиента из таблицы one_load_history"""
        if not self.connect():
            return None
        
        try:
            cursor = self.connection.cursor(as_dict=True)
            
            # ПРЯМОЙ ЗАПРОС к one_load_history (как вы указали в примере SQL)
            query = """
            SELECT *
            FROM one_load_history
            WHERE id = %s
            ORDER BY id
            """
            
            self.logger.log(f"Выполняем запрос к one_load_history: {query} с client_id={client_id}", "INFO")
            cursor.execute(query, (client_id,))
            results = cursor.fetchall()
            
            self.logger.log(f"Найдено записей для клиента {client_id}: {len(results)}", "INFO")
            
            if results:
                # Показываем структуру первой записи для отладки
                first_record = results[0]
                self.logger.log(f"Структура первой записи:", "INFO")
                for key in first_record.keys():
                    self.logger.log(f"  {key}: {type(first_record[key])} = {first_record[key]}", "INFO")
            
            return results
            
        except Exception as e:
            self.logger.log(f"Ошибка получения документов: {e}", "ERROR")
            # Возвращаем пустой список при ошибке
            return []
        finally:
            self.disconnect()
    
    def get_document_type_info(self):
        """Получает информацию о типах документов из системных таблиц"""
        if not self.connect():
            return None
        
        try:
            cursor = self.connection.cursor(as_dict=True)
            
            # Ищем таблицу со справочником типов документов
            # Обычно такие таблицы называются type_doc, doc_types, document_types и т.д.
            possible_tables = [
                'type_doc',
                'doc_types', 
                'document_types',
                'spr_doc_type',
                'spr_type_doc',
                'reference_doc_type',
                'dict_doc_type'
            ]
            
            for table_name in possible_tables:
                cursor.execute("""
                    SELECT TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = %s
                """, (table_name,))
                
                if cursor.fetchone():
                    # Получаем данные из таблицы типов документов
                    query = f"""
                    SELECT TOP 10 *
                    FROM {table_name}
                    """
                    
                    cursor.execute(query)
                    results = cursor.fetchall()
                    
                    self.logger.log(f"Найдена таблица типов документов: {table_name}", "INFO")
                    return {
                        'table_name': table_name,
                        'data': results
                    }
            
            # Если не нашли таблицу, пробуем найти через INFORMATION_SCHEMA
            self.logger.log("Таблица типов документов не найдена по имени, ищем через колонки...", "INFO")
            
            cursor.execute("""
                SELECT DISTINCT t.TABLE_NAME, c.COLUMN_NAME
                FROM INFORMATION_SCHEMA.TABLES t
                JOIN INFORMATION_SCHEMA.COLUMNS c ON t.TABLE_NAME = c.TABLE_NAME
                WHERE c.COLUMN_NAME LIKE '%type_doc%'
                   OR c.COLUMN_NAME LIKE '%doc_type%'
                   OR c.COLUMN_NAME LIKE '%type%doc%'
                AND t.TABLE_TYPE = 'BASE TABLE'
                ORDER BY t.TABLE_NAME
            """)
            
            tables_with_type_doc = cursor.fetchall()
            
            if tables_with_type_doc:
                self.logger.log(f"Найдены таблицы с type_doc: {tables_with_type_doc}", "INFO")
                return {
                    'message': f"Найдены таблицы с колонками type_doc: {tables_with_type_doc}",
                    'tables': tables_with_type_doc
                }
            
            return None
            
        except Exception as e:
            self.logger.log(f"Ошибка поиска типов документов: {e}", "ERROR")
            return None
        finally:
            self.disconnect()


    def test_document_query(self, client_id):
        """Тестирует запрос для поиска документов (для отладки)"""
        if not self.connect():
            return None
        
        try:
            cursor = self.connection.cursor(as_dict=True)
            
            # Пробуем прямой запрос к one_load_history
            query = """
            SELECT TOP 10 *
            FROM one_load_history
            WHERE id = %s
            """
            
            self.logger.log(f"Тестовый запрос: {query}", "INFO")
            cursor.execute(query, (client_id,))
            results = cursor.fetchall()
            
            if results:
                self.logger.log(f"Тестовый запрос успешен! Найдено: {len(results)} записей", "SUCCESS")
                
                # Показываем структуру первой записи
                if results:
                    first_record = results[0]
                    self.logger.log(f"Структура записи:", "INFO")
                    for key in first_record.keys():
                        self.logger.log(f"  {key}: {type(first_record[key])}", "INFO")
            
            return results
            
        except Exception as e:
            self.logger.log(f"Ошибка тестового запроса: {e}", "ERROR")
            return None
        finally:
            self.disconnect()
    
    def test_connection(self):
        """Тестирует подключение к базе данных"""
        self.logger.log("Тестирование подключения к БД...", "INFO")
        
        # Пробуем подключиться к указанной БД
        if self.connect():
            self.logger.log(f"База данных '{self.current_database}' доступна", "SUCCESS")
            self.disconnect()
            return True
        
        self.logger.log("База данных недоступна", "ERROR")
        return False
    
    def test_document_query(self, client_id):
        """Тестирует запрос для поиска документов (для отладки)"""
        if not self.connect():
            return None
        
        try:
            cursor = self.connection.cursor(as_dict=True)
            
            # Пробуем прямой запрос к one_load_history
            query = """
            SELECT TOP 10 *
            FROM one_load_history
            WHERE id = %s
            """
            
            self.logger.log(f"Тестовый запрос: {query}", "INFO")
            cursor.execute(query, (client_id,))
            results = cursor.fetchall()
            
            if results:
                self.logger.log(f"Тестовый запрос успешен! Найдено: {len(results)} записей", "SUCCESS")
                
                # Показываем структуру первой записи
                if results:
                    first_record = results[0]
                    self.logger.log(f"Структура записи:", "INFO")
                    for key in first_record.keys():
                        self.logger.log(f"  {key}: {type(first_record[key])}", "INFO")
            
            return results
            
        except Exception as e:
            self.logger.log(f"Ошибка тестового запроса: {e}", "ERROR")
            return None
        finally:
            self.disconnect()