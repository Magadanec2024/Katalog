# modules/database.py
import sqlite3
import os
from contextlib import contextmanager
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path="data/database.db"):
        self.db_path = db_path
        self.ensure_data_directory()
        self.init_database()
        self.migrate_database()  # Добавляем миграцию

    def ensure_data_directory(self):
        """Создание директории data, если она не существует"""
        os.makedirs("data", exist_ok=True)
        logger.debug("Директория 'data' проверена/создана")

    def migrate_database(self):
        """Миграция базы данных - добавление недостающих столбцов"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Проверяем и добавляем столбец surname если его нет
                try:
                    cursor.execute("SELECT surname FROM employees LIMIT 1")
                    logger.debug("Столбец 'surname' уже существует")
                except sqlite3.OperationalError:
                    cursor.execute("ALTER TABLE employees ADD COLUMN surname TEXT DEFAULT ''")
                    logger.info("Добавлен столбец 'surname' в таблицу employees")

                # Проверяем и добавляем столбец position если его нет
                try:
                    cursor.execute("SELECT position FROM employees LIMIT 1")
                    logger.debug("Столбец 'position' уже существует")
                except sqlite3.OperationalError:
                    cursor.execute("ALTER TABLE employees ADD COLUMN position TEXT DEFAULT ''")
                    logger.info("Добавлен столбец 'position' в таблицу employees")

                # Обновляем существующие записи
                cursor.execute("UPDATE employees SET surname = '' WHERE surname IS NULL")
                cursor.execute("UPDATE employees SET position = '' WHERE position IS NULL")

                conn.commit()
                logger.info("Миграция базы данных завершена успешно")

        except Exception as e:
            logger.error(f"Ошибка при миграции базы данных: {e}", exc_info=True)

    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        logger.info("Начало инициализации базы данных")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            logger.debug("Подключение к базе данных установлено")

            # Создание таблицы сотрудников - ОБНОВЛЕННАЯ ВЕРСИЯ
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    surname TEXT DEFAULT '',
                    position TEXT DEFAULT ''
                )
            ''')
            logger.debug("Таблица 'employees' создана или уже существует")

            # Создание таблицы ставок (если еще не создана)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    operation_name TEXT NOT NULL,
                    rate_per_hour REAL DEFAULT 0.0,
                    rate_per_minute REAL DEFAULT 0.0,
                    rate_per_second REAL DEFAULT 0.0,
                    old_rate REAL DEFAULT 0.0,
                    new_rate REAL DEFAULT 0.0
                )
            ''')
            logger.debug("Таблица 'rates' создана или уже существует")

            # Создание таблицы операций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operations_list (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    rate_per_minute REAL DEFAULT 0.0
                )
            ''')
            logger.debug("Таблица 'operations_list' создана или уже существует")

            # Создание таблицы материалов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    name TEXT NOT NULL,
                    diameter REAL,
                    section_length REAL,
                    section_width REAL,
                    thickness REAL,
                    weight_per_meter REAL,
                    purchase_price_t REAL,
                    delivery_price_t REAL,
                    waste_price REAL,
                    final_price_kg REAL,
                    unit_of_measurement TEXT,
                    our_price_per_kg REAL  -- Наша цена за кг
                )
            ''')
            logger.debug("Таблица 'materials' создана или уже существует")

            # Создание таблицы изделий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT,
                    article TEXT,
                    name TEXT NOT NULL,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            logger.debug("Таблица 'products' создана или уже существует")

            # Создание таблицы операций для изделий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    operation_name TEXT NOT NULL,
                    quantity_measured INTEGER,
                    time_measured REAL,
                    time_per_unit REAL,
                    rate_per_minute REAL,
                    cost REAL,
                    employee_id INTEGER,
                    approved_rate REAL DEFAULT NULL, -- Новый столбец
                    FOREIGN KEY (product_id) REFERENCES products (id),
                    FOREIGN KEY (employee_id) REFERENCES employees (id) -- Внешний ключ
                )
            ''')
            logger.debug("Таблица 'operations' создана или уже существует")

            # Создание таблицы материалов изделия
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS product_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    material_id INTEGER,
                    length REAL,
                    width REAL,
                    thickness REAL,
                    quantity INTEGER,
                    cost REAL,
                    FOREIGN KEY (product_id) REFERENCES products (id),
                    FOREIGN KEY (material_id) REFERENCES materials (id)
                )
            ''')
            logger.debug("Таблица 'product_materials' создана или уже существует")

            # удалить фрагмент # Создание таблицы изделий с полями для цены
            # cursor.execute('''
            #             CREATE TABLE IF NOT EXISTS products (
            #                 id INTEGER PRIMARY KEY AUTOINCREMENT,
            #                 product_id TEXT,
            #                 article TEXT,
            #                 name TEXT NOT NULL,
            #                 overhead_percent REAL DEFAULT 0.55,
            #                 profit_percent REAL DEFAULT 0.30,
            #                 approved_price REAL DEFAULT 0.0,
            #                 created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            #             )
            #         ''')
            # logger.debug("Таблица 'products' создана или уже существует")

            # Добавляем стандартные операции, если их нет
            cursor.execute("SELECT COUNT(*) FROM operations_list")
            if cursor.fetchone()[0] == 0:
                default_operations = [
                    ("Токарная обработка", 2.5),
                    ("Фрезерование", 3.0),
                    ("Сверление", 1.5),
                    ("Шлифовка", 2.0),
                    ("Сборка", 1.8),
                    ("Покраска", 2.2)
                ]

                cursor.executemany(
                    "INSERT INTO operations_list (name, rate_per_minute) VALUES (?, ?)",
                    default_operations
                )
                logger.info("Добавлены стандартные операции")

            # Загрузка сотрудников из Excel (если файл существует)
            self.load_employees_from_excel()

            conn.commit()
            logger.info("Инициализация базы данных завершена успешно")

    def load_employees_from_excel(self):
        """Загрузка сотрудников из Excel файла - ТОЛЬКО ЕСЛИ БД ПУСТАЯ"""
        import pandas as pd
        excel_path = "data/employees.xlsx"

        try:
            # ПРОВЕРЯЕМ, ЕСТЬ ЛИ УЖЕ СОТРУДНИКИ В БД
            result = self.fetch_one("SELECT COUNT(*) FROM employees")
            employee_count = result[0] if result else 0

            if employee_count > 0:
                logger.info(f"В БД уже есть {employee_count} сотрудников, пропускаем загрузку из Excel")
                return

            # Если БД пустая - проверяем файл
            if not os.path.exists(excel_path):
                logger.warning(f"Файл сотрудников {excel_path} не найден. Будет создан при первом экспорте.")
                self._add_default_employee()
                return

            # Загружаем из Excel
            logger.info("БД пустая, загружаем сотрудников из Excel")
            df = pd.read_excel(excel_path, sheet_name="Сотрудники", header=0)

            # Берем ПЕРВЫЙ СТОЛБЕЦ
            first_column = df.columns[0]
            df = df.dropna(subset=[first_column])
            employees = df[first_column].tolist()

            if not employees:
                logger.warning("В файле Excel нет сотрудников")
                self._add_default_employee()
                return

            logger.debug(f"Найдены сотрудники: {employees}")

            for emp_name in employees:
                query = "INSERT INTO employees (name) VALUES (?)"
                self.execute_query(query, (str(emp_name).strip(),))

            logger.info(f"Загружено {len(employees)} сотрудников из Excel.")

        except Exception as e:
            logger.error(f"Ошибка при загрузке сотрудников из Excel: {e}", exc_info=True)
            self._add_default_employee()

    def _add_default_employee(self):
        """Добавление сотрудника по умолчанию если файл не найден или ошибка"""
        # ИСПРАВЛЕННЫЙ КОД - используем fetch_one вместо execute_query
        result = self.fetch_one("SELECT COUNT(*) FROM employees")
        employee_count = result[0] if result else 0

        if employee_count == 0:
            self.execute_query("INSERT INTO employees (name) VALUES (?)", ("Не назначен",))
            logger.info("Добавлен сотрудник 'Не назначен' по умолчанию.")

    def _create_example_employees_file(self, file_path):
        """Создание примера файла сотрудников"""
        try:
            import pandas as pd

            # Создаем данные для примера
            example_data = {
                'ФИО': [
                    'Иванов Иван Иванович',
                    'Петров Петр Петрович',
                    'Сидорова Мария Сергеевна'
                ]
            }

            df = pd.DataFrame(example_data)

            # Создаем директорию если нет
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Сохраняем файл
            df.to_excel(file_path, sheet_name='Сотрудники', index=False)
            logger.info(f"Создан пример файла сотрудников: {file_path}")

        except Exception as e:
            logger.error(f"Ошибка при создании примера файла сотрудников: {e}")

    def _add_default_employee(self):
        """Добавление сотрудника по умолчанию если файл не найден или ошибка"""
        cursor = self.execute_query("SELECT COUNT(*) FROM employees")
        if cursor.fetchone()[0] == 0:
            self.execute_query("INSERT INTO employees (name) VALUES (?)", ("Не назначен",))
            logger.info("Добавлен сотрудник 'Не назначен' по умолчанию.")

    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для подключения к базе данных"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка в контекстном менеджере БД: {e}", exc_info=True)
            raise e
        finally:
            conn.close()

    def execute_query(self, query, params=None):
        """Выполнение запроса к базе данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.fetchall()

    def fetch_all(self, query, params=None):
        """Получение всех записей из базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()

    def fetch_one(self, query, params=None):
        """Получение одной записи из базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchone()
