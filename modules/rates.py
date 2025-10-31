# modules/rates.py
import pandas as pd
import re
from modules.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)


class RateManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def load_rates_from_excel(self, file_path):
        """Загрузка ставок из Excel файла"""
        logger.info(f"[СТАВКИ] Начало загрузки ставок из файла: {file_path}")
        try:
            # Читаем Excel файл, указывая лист "ставки" и используя третью строку как заголовки
            # (Первые две строки: "ставки" и "СТЕМЕТ/МЕТАЛЛ")
            df = pd.read_excel(file_path, sheet_name="ставки", header=2)

            # Удаляем строки, которые содержат только NaN или пустые значения
            df = df.dropna(how='all')

            # Очистка существующих ставок
            self.db_manager.execute_query("DELETE FROM operations_list")
            logger.debug("[СТАВКИ] Очищены существующие ставки из БД")

            # Вставка новых ставок
            inserted_count = 0
            for index, row in df.iterrows():
                # Пропускаем строку, если в ней нет названия операции или это строка с итогами
                # Также проверяем, что это не заголовки следующей таблицы (например, "диаметр", "длина", "вес")
                operation_name = row.get('ОПЕРАЦИИ', '')
                if pd.isna(operation_name) or operation_name == '' or operation_name == 'Итог':
                    continue

                # Проверяем, является ли это заголовком следующей таблицы
                if operation_name in ['диаметр', 'длина', 'вес', 'Расценки с 01.05.2025', 'Сумма',
                                      'Расценки с 01.02.2025', 'Старые расценки', 'Количество', 'Время',
                                      'Рабочих дней', 'Рабочих часов в день', 'Минут в часе',
                                      'Рабочих секунд в месяц', 'Рабочих минут в месяц', 'Рабочих часов в месяц']:
                    break  # Прекращаем обработку, так как дошли до следующей таблицы

                query = """
                    INSERT INTO operations_list 
                    (name, rate_per_minute)
                    VALUES (?, ?)
                """

                # Функция для безопасного преобразования значений в float
                def safe_float(val):
                    try:
                        if pd.isna(val) or val == '' or val is None:
                            return 0.0
                        # Проверяем, является ли значение строкой
                        if isinstance(val, str):
                            # Ищем числовые значения в строке
                            numbers = re.findall(r'[\d.,]+', val)
                            if numbers:
                                # Берем первое найденное число и заменяем запятую на точку
                                num_str = numbers[0].replace(',', '.')
                                try:
                                    return float(num_str)
                                except ValueError:
                                    return 0.0
                            else:
                                return 0.0
                        return float(val)
                    except (ValueError, TypeError, AttributeError):
                        return 0.0

                # Функция для безопасного преобразования значений в строку
                def safe_str(val):
                    try:
                        if pd.isna(val) or val is None:
                            return ''
                        # Преобразуем в строку и убираем лишние пробелы
                        return str(val).strip()
                    except:
                        return ''

                params = (
                    safe_str(operation_name),
                    safe_float(row.get('грн/мин', 0.0))
                )

                self.db_manager.execute_query(query, params)
                inserted_count += 1
                logger.debug(f"[СТАВКИ] Добавлена операция: {params[0]} - {params[1]} грн/мин")

            logger.info(f"[СТАВКИ] Загружено {inserted_count} строк из Excel файла ставок")
            return True
        except Exception as e:
            logger.error(f"[СТАВКИ] Ошибка при загрузке ставок: {e}", exc_info=True)
            return False

    def get_all_operations(self):
        """Получение всех операций"""
        logger.debug("[СТАВКИ] Получение всех операций из БД")
        query = "SELECT name, rate_per_minute FROM operations_list ORDER BY name"
        return self.db_manager.fetch_all(query)

    def get_rate_by_operation(self, operation_name):
        """Получение ставки по названию операции"""
        logger.debug(f"[СТАВКИ] Получение ставки для операции: {operation_name}")
        query = "SELECT rate_per_minute FROM operations_list WHERE name = ?"
        result = self.db_manager.fetch_one(query, (operation_name,))
        if result:
            rate = result[0]
            logger.debug(f"[СТАВКИ] Найдена ставка для операции '{operation_name}': {rate} грн/мин")
            return rate
        logger.debug(f"[СТАВКИ] Ставка для операции '{operation_name}' не найдена, возвращаем 0.0")
        return 0.0
