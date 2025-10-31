# modules/materials.py
import pandas as pd
import re
from modules.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)


class MaterialManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def load_materials_from_excel(self, file_path):
        """Загрузка материалов из Excel файла"""
        logger.info(f"[МАТЕРИАЛЫ] Начало загрузки материалов из файла: {file_path}")
        try:
            # Читаем Excel файл, указывая лист "материалы" и используя вторую строку как заголовки
            df = pd.read_excel(file_path, sheet_name="материалы", header=1)

            # Удаляем строки, которые содержат только NaN или пустые значения
            df = df.dropna(how='all')

            # Очистка существующих материалов
            self.db_manager.execute_query("DELETE FROM materials")
            logger.debug("[МАТЕРИАЛЫ] Очищены существующие материалы из БД")

            # Вставка новых материалов
            inserted_count = 0
            for index, row in df.iterrows():
                # Пропускаем строку, если в ней нет наименования материала
                if pd.isna(row.get('Наименование материала', '')) or row['Наименование материала'] == '':
                    continue

                query = """
                    INSERT INTO materials 
                    (category, name, diameter, section_length, section_width, 
                     thickness, weight_per_meter, purchase_price_t, delivery_price_t,
                     waste_price, final_price_kg, unit_of_measurement, our_price_per_kg)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    safe_str(row.get('Категория', '')),
                    safe_str(row.get('Наименование материала', '')),
                    safe_float(row.get('диаметр', 0.0)),
                    safe_float(row.get('Сечение_длина', 0.0)),
                    safe_float(row.get('Сечение_ширина', 0.0)),
                    safe_float(row.get('Толщина', 0.0)),
                    safe_float(row.get('Вес 1 м, кг', 0.0)),
                    safe_float(row.get('закупка розн/т ', 0.0)),
                    safe_float(row.get('доставка/т + 3 % к закупочной цене', 0.0)),
                    safe_float(row.get('Брак, остатки (3%) + к закупочной цене', 0.0)),
                    safe_float(row.get('Выходит закупка в грн./ 1 кг', 0.0)),
                    safe_str(row.get('unit_of_measurement', '')),
                    safe_float(row.get('Наша продажа/кг', 0.0))  # Наша цена за кг
                )

                self.db_manager.execute_query(query, params)
                inserted_count += 1
                logger.debug(f"[МАТЕРИАЛЫ] Добавлен материал: {params[1]}")

            logger.info(f"[МАТЕРИАЛЫ] Загружено {inserted_count} строк из Excel файла материалов")
            return True
        except Exception as e:
            logger.error(f"[МАТЕРИАЛЫ] Ошибка при загрузке материалов: {e}", exc_info=True)
            return False

    def get_all_materials(self):
        """Получение всех материалов"""
        logger.debug("[МАТЕРИАЛЫ] Получение всех материалов из БД")
        query = "SELECT id, name FROM materials ORDER BY name"
        return self.db_manager.fetch_all(query)

    def get_categories(self):
        """Получение всех категорий материалов"""
        logger.debug("[МАТЕРИАЛЫ] Получение всех категорий материалов из БД")
        query = "SELECT DISTINCT category FROM materials WHERE category != '' ORDER BY category"
        categories = self.db_manager.fetch_all(query)
        return [row[0] for row in categories]

    def get_materials_by_category(self, category):
        """Получение материалов по категории"""
        logger.debug(f"[МАТЕРИАЛЫ] Получение материалов по категории: {category}")
        query = "SELECT id, name FROM materials WHERE category = ? ORDER BY name"
        return self.db_manager.fetch_all(query, (category,))

    def get_material_by_id(self, material_id):
        """Получение материала по ID"""
        logger.debug(f"[МАТЕРИАЛЫ] Получение материала по ID: {material_id}")
        query = "SELECT * FROM materials WHERE id = ?"
        return self.db_manager.fetch_one(query, (material_id,))

    def get_material_by_name(self, name):
        """Получение материала по названию"""
        logger.debug(f"[МАТЕРИАЛЫ] Получение материала по названию: {name}")
        query = "SELECT * FROM materials WHERE name = ?"
        return self.db_manager.fetch_one(query, (name,))
