# modules/interface.py

import sys
import os

from pathlib import Path

# Автоматически находим путь к плагинам в текущем виртуальном окружении
venv_base = Path(sys.executable).parent.parent  # поднимаемся из Scripts/
plugins_path = venv_base / "Lib" / "site-packages" / "PyQt5" / "Qt5" / "plugins"

if plugins_path.exists():
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins_path)
import logger
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QLabel, QSpinBox, QDoubleSpinBox, QHeaderView,
    QSplitter, QListWidget, QListWidgetItem, QFrame, QMessageBox, QFileDialog,
    QStackedWidget, QTextEdit, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
try:
    from modules.database import DatabaseManager
    from modules.materials import MaterialManager # Убедиться, что импортируется из main_interface

    # from modules.reports import ReportManager - импортируем по необходимости
except ImportError as e:
    logger.critical(f"Критическая ошибка импорта модулей: {e}", exc_info=True)
    QMessageBox.critical(None, "Ошибка импорта", f"Не удалось импортировать необходимые модули: {e}")
    sys.exit(1)
from modules.rates import RateManager
from modules.products import ProductManager
from modules.calculations import CalculationManager
from modules.reports import ReportManager
import logging

logger = logging.getLogger(__name__)


class MainInterface:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.material_manager = MaterialManager(db_manager)
        self.rate_manager = RateManager(db_manager)
        self.product_manager = ProductManager(db_manager)
        self.calculation_manager = CalculationManager(db_manager)
        self.report_manager = ReportManager(db_manager)

        # Инициализация данных
        self.current_product_id = None
        self.operations_data = []
        self.materials_data = []

        # Инициализация атрибутов интерфейса
        self._init_ui_components()

        # Создание вкладок
        self.input_tab = self.create_input_tab()
        self.catalog_tab = self.create_catalog_tab()

        # Загрузка начальных данных
        self.load_initial_data()

    def _init_ui_components(self):
        """Инициализация компонентов интерфейса"""
        logger.debug("Инициализация UI компонентов")
        # Поля ввода основной информации
        self.product_id_input = None
        self.article_input = None
        self.name_input = None

        # Компоненты операций
        self.operation_combo = None
        self.employee_combo = None
        self.quantity_measured_input = None
        self.time_measured_input = None
        self.add_operation_btn = None
        self.delete_operation_btn = None
        self.update_operation_btn = None
        self.operations_table = None

        # Компоненты материалов
        self.category_combo = None
        self.material_combo = None
        self.material_type_widget = None
        self.length_input = None
        self.length_input_2 = None  # для второго виджета
        self.width_input = None
        self.thickness_input = None
        self.quantity_input = None
        self.quantity_input_2 = None  # для второго виджета
        self.quantity_input_3 = None  # для третьего виджета
        self.add_material_btn = None
        self.delete_material_btn = None
        self.update_material_btn = None
        self.materials_table = None

        # Компоненты каталога
        self.search_input = None
        self.products_list = None
        self.refresh_btn = None
        self.export_btn = None

    def create_input_tab(self):
        """Создание вкладки ввода данных"""
        logger.debug("Создание вкладки ввода данных")
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Основная информация об изделии
        info_group = self.create_product_info_group()
        layout.addWidget(info_group)

        # Группы операций и материалов
        operations_materials_splitter = QSplitter(Qt.Horizontal)

        # Группа технологических операций
        operations_group = self.create_operations_group()
        operations_materials_splitter.addWidget(operations_group)

        # Группа материалов
        materials_group = self.create_materials_group()
        operations_materials_splitter.addWidget(materials_group)

        layout.addWidget(operations_materials_splitter)

        return widget

    def create_product_info_group(self):
        """Создание группы с основной информацией об изделии"""
        logger.debug("Создание группы информации об изделии")
        group = QGroupBox("Информация об изделии")
        layout = QFormLayout(group)

        # Поля ввода
        self.product_id_input = QLineEdit()
        self.article_input = QLineEdit()
        self.name_input = QLineEdit()

        layout.addRow("ID:", self.product_id_input)
        layout.addRow("Артикул:", self.article_input)
        layout.addRow("Название изделия:", self.name_input)

        return group

    def create_operations_group(self):
        """Создание группы технологических операций"""
        logger.debug("Создание группы операций")
        group = QGroupBox("Тех. процессы")
        layout = QVBoxLayout(group)

        # Выпадающий список операций
        operations_layout = QHBoxLayout()
        self.operation_combo = QComboBox()
        operations_layout.addWidget(QLabel("Операция:"))
        operations_layout.addWidget(self.operation_combo)
        layout.addLayout(operations_layout)

        # Выпадающий список сотрудников
        employee_layout = QHBoxLayout()
        self.employee_combo = QComboBox()
        employee_layout.addWidget(QLabel("Сотрудник:"))
        employee_layout.addWidget(self.employee_combo)
        layout.addLayout(employee_layout)

        # Поля для ввода данных
        input_layout = QFormLayout()
        self.quantity_measured_input = QSpinBox()
        self.quantity_measured_input.setRange(1, 9999)
        self.time_measured_input = QDoubleSpinBox()
        self.time_measured_input.setRange(0.0, 9999.0)
        self.time_measured_input.setDecimals(2)

        input_layout.addRow("Кол-во по замерам:", self.quantity_measured_input)
        input_layout.addRow("Время замера (мин):", self.time_measured_input)
        layout.addLayout(input_layout)

        # Кнопки добавления, обновления и удаления операции
        buttons_layout = QHBoxLayout()
        self.add_operation_btn = QPushButton("Добавить операцию")
        self.update_operation_btn = QPushButton("Обновить операцию")
        self.delete_operation_btn = QPushButton("Удалить операцию")
        buttons_layout.addWidget(self.add_operation_btn)
        buttons_layout.addWidget(self.update_operation_btn)
        buttons_layout.addWidget(self.delete_operation_btn)
        layout.addLayout(buttons_layout)

        # Таблица с операциями
        self.operations_table = QTableWidget()
        self.operations_table.setColumnCount(8)
        self.operations_table.setHorizontalHeaderLabels([
            "Операция", "Кол-во по замерам", "Время замера (мин)",
            "Время на 1 деталь (мин)", "Ставка (грн/мин)", "Стоимость (грн)",
            "Сотрудник", "Утверждённая расценка"
        ])
        self.operations_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.operations_table)

        return group

    def create_materials_group(self):
        """Создание группы материалов"""
        logger.debug("Создание группы материалов")
        group = QGroupBox("Материалы")
        layout = QVBoxLayout(group)

        # Выпадающий список категорий
        category_layout = QHBoxLayout()
        self.category_combo = QComboBox()
        category_layout.addWidget(QLabel("Категория:"))
        category_layout.addWidget(self.category_combo)
        layout.addLayout(category_layout)

        # Выпадающий список материалов
        materials_layout = QHBoxLayout()
        self.material_combo = QComboBox()
        materials_layout.addWidget(QLabel("Материал:"))
        materials_layout.addWidget(self.material_combo)
        layout.addLayout(materials_layout)

        # Виджет для разных типов материалов
        self.material_type_widget = QStackedWidget()

        # Виджет для материалов с длиной и количеством (трубы, проволока, профиль)
        length_quantity_widget = QWidget()
        length_quantity_layout = QFormLayout(length_quantity_widget)
        self.length_input = QDoubleSpinBox()
        self.length_input.setRange(0.0, 9999.0)
        self.length_input.setDecimals(3)
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 9999)
        length_quantity_layout.addRow("Длина (м):", self.length_input)
        length_quantity_layout.addRow("Количество шт.:", self.quantity_input)
        self.material_type_widget.addWidget(length_quantity_widget)

        # Виджет для листовых материалов (длина, ширина, толщина, количество)
        dimensions_widget = QWidget()
        dimensions_layout = QFormLayout(dimensions_widget)
        self.length_input_2 = QDoubleSpinBox()
        self.length_input_2.setRange(0.0, 9999.0)
        self.length_input_2.setDecimals(3)
        self.width_input = QDoubleSpinBox()
        self.width_input.setRange(0.0, 9999.0)
        self.width_input.setDecimals(3)
        self.thickness_input = QDoubleSpinBox()
        self.thickness_input.setRange(0.0, 9999.0)
        self.thickness_input.setDecimals(3)
        self.quantity_input_2 = QSpinBox()
        self.quantity_input_2.setRange(1, 9999)
        dimensions_layout.addRow("Длина (м):", self.length_input_2)
        dimensions_layout.addRow("Ширина (м):", self.width_input)
        dimensions_layout.addRow("Толщина (м):", self.thickness_input)
        dimensions_layout.addRow("Количество шт.:", self.quantity_input_2)
        self.material_type_widget.addWidget(dimensions_widget)

        # Виджет для материалов с количеством (метизы)
        quantity_only_widget = QWidget()
        quantity_only_layout = QFormLayout(quantity_only_widget)
        self.quantity_input_3 = QSpinBox()
        self.quantity_input_3.setRange(1, 999999)
        quantity_only_layout.addRow("Количество шт.:", self.quantity_input_3)
        self.material_type_widget.addWidget(quantity_only_widget)

        layout.addWidget(self.material_type_widget)

        # Кнопки добавления, обновления и удаления материала
        buttons_layout = QHBoxLayout()
        self.add_material_btn = QPushButton("Добавить материал")
        self.update_material_btn = QPushButton("Обновить материал")
        self.delete_material_btn = QPushButton("Удалить выбранный материал")
        buttons_layout.addWidget(self.add_material_btn)
        buttons_layout.addWidget(self.update_material_btn)
        buttons_layout.addWidget(self.delete_material_btn)
        layout.addLayout(buttons_layout)

        # Таблица с материалами
        self.materials_table = QTableWidget()
        self.materials_table.setColumnCount(5)
        self.materials_table.setHorizontalHeaderLabels([
            "Материал", "Длина (м)", "Ширина (м)", "Количество (шт)", "Стоимость (грн)"
        ])
        self.materials_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.materials_table)

        return group

    def create_catalog_tab(self):
        """Создание вкладки каталога"""
        logger.debug("Создание вкладки каталога")
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Поиск и фильтрация
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по артикулу или названию...")
        search_layout.addWidget(QLabel("Поиск:"))
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Список изделий
        self.products_list = QListWidget()
        layout.addWidget(self.products_list)

        # Кнопки управления
        buttons_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Обновить")
        self.export_btn = QPushButton("Экспорт в Excel")
        buttons_layout.addWidget(self.refresh_btn)
        buttons_layout.addWidget(self.export_btn)
        layout.addLayout(buttons_layout)

        return widget

    def load_initial_data(self):
        """Загрузка начальных данных"""
        logger.debug("Загрузка начальных данных")
        # Подключение сигналов
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        self.material_combo.currentIndexChanged.connect(self.on_material_changed)
        self.add_operation_btn.clicked.connect(self.add_operation)
        self.update_operation_btn.clicked.connect(self.update_selected_operation)
        self.delete_operation_btn.clicked.connect(self.delete_selected_operation)
        self.add_material_btn.clicked.connect(self.add_material)
        self.update_material_btn.clicked.connect(self.update_selected_material)
        self.delete_material_btn.clicked.connect(self.delete_selected_material)
        self.refresh_btn.clicked.connect(self.refresh_products_list)
        self.export_btn.clicked.connect(self.export_selected_product)

        # Загрузка операций и материалов в комбобоксы
        self.load_operations_to_combo()
        self.load_employees_to_combo()
        self.load_categories_to_combo()

        # Загрузка списка изделий
        self.refresh_products_list()

    def load_employees_to_combo(self):
        """Загрузка сотрудников в комбобокс"""
        logger.debug("Загрузка сотрудников в комбобокс")
        query = "SELECT id, name FROM employees ORDER BY name"
        employees = self.db_manager.fetch_all(query)
        self.employee_combo.clear()
        self.employee_combo.addItem("", None)  # Пустой элемент для "не выбрано"

        for emp_id, emp_name in employees:
            self.employee_combo.addItem(emp_name, emp_id)

    def load_operations_to_combo(self):
        """Загрузка операций в комбобокс"""
        logger.debug("Загрузка операций в комбобокс")
        operations = self.rate_manager.get_all_operations()
        self.operation_combo.clear()

        for operation_name, rate_per_minute in operations:
            self.operation_combo.addItem(operation_name)

    def load_categories_to_combo(self):
        """Загрузка категорий в комбобокс"""
        logger.debug("Загрузка категорий в комбобокс")
        categories = self.material_manager.get_categories()
        self.category_combo.clear()

        for category in categories:
            self.category_combo.addItem(category)

    def on_category_changed(self, category):
        """Обработка изменения выбранной категории"""
        logger.debug(f"Изменена категория на: {category}")
        try:
            materials = self.material_manager.get_materials_by_category(category)
            self.material_combo.clear()

            for material_id, material_name in materials:
                self.material_combo.addItem(material_name, material_id)
        except Exception as e:
            logger.error(f"Ошибка при загрузке материалов по категории: {e}", exc_info=True)
            QMessageBox.critical(None, "Ошибка", f"Ошибка при загрузке материалов: {e}")

    def on_material_changed(self):
        """Обработка изменения выбранного материала"""
        logger.debug("Изменен выбранный материал")
        try:
            # Получаем информацию о материале
            current_material_id = self.material_combo.currentData()
            if current_material_id:
                material_info = self.material_manager.get_material_by_id(current_material_id)
                if material_info and len(material_info) >= 14:  # Проверяем, что у нас достаточно данных
                    # Определяем тип материала по категории
                    category = material_info[1]  # индекс категории в базе данных

                    # Определяем, какие поля ввода показывать
                    if category in ['Труба', 'Проволока', 'Профиль', 'Профиль г/к', 'Прут']:
                        # Материал с длиной и количеством
                        self.material_type_widget.setCurrentIndex(0)
                    elif category == 'Лист':
                        # Листовой материал с размерами
                        self.material_type_widget.setCurrentIndex(1)
                    elif category == 'Метизы':
                        # Метизы - только количество
                        self.material_type_widget.setCurrentIndex(2)
                    else:
                        # По умолчанию - длина и количество
                        self.material_type_widget.setCurrentIndex(0)
                else:
                    logger.debug(f"Недостаточно данных для материала ID {current_material_id}")
        except Exception as e:
            logger.error(f"Ошибка при обработке изменения материала: {e}", exc_info=True)
            QMessageBox.critical(None, "Ошибка", f"Ошибка при обработке материала: {e}")

    def add_operation(self):
        """Добавление операции"""
        logger.debug("Добавление операции")
        operation_name = self.operation_combo.currentText()
        employee_id = self.employee_combo.currentData()  # Получаем ID сотрудника
        employee_name = self.employee_combo.currentText()  # Получаем имя сотрудника
        quantity_measured = self.quantity_measured_input.value()
        time_measured = self.time_measured_input.value()

        if not operation_name:
            QMessageBox.warning(None, "Ошибка", "Выберите операцию")
            return

        if quantity_measured == 0:
            QMessageBox.warning(None, "Ошибка", "Количество по замерам не может быть 0")
            return

        # Получаем ставку для операции из базы данных
        rate_per_minute = self.rate_manager.get_rate_by_operation(operation_name)

        if rate_per_minute == 0:
            rate_per_minute = 2.0  # Значение по умолчанию

        # Расчет времени на 1 деталь
        time_per_unit = time_measured / quantity_measured if quantity_measured != 0 else 0

        # Расчет стоимости
        cost = time_per_unit * rate_per_minute

        # Добавление в таблицу
        row = self.operations_table.rowCount()
        self.operations_table.insertRow(row)

        self.operations_table.setItem(row, 0, QTableWidgetItem(operation_name))
        self.operations_table.setItem(row, 1, QTableWidgetItem(str(quantity_measured)))
        self.operations_table.setItem(row, 2, QTableWidgetItem(f"{time_measured:.2f}"))
        self.operations_table.setItem(row, 3, QTableWidgetItem(f"{time_per_unit:.2f}"))
        self.operations_table.setItem(row, 4, QTableWidgetItem(f"{rate_per_minute:.2f}"))
        self.operations_table.setItem(row, 5, QTableWidgetItem(f"{cost:.2f}"))
        self.operations_table.setItem(row, 6, QTableWidgetItem(employee_name))  # Сотрудник
        self.operations_table.setItem(row, 7, QTableWidgetItem(""))  # Утверждённая расценка (пока пусто)

        # Сохранение данных
        self.operations_data.append({
            'operation_name': operation_name,
            'employee_id': employee_id,
            'employee_name': employee_name,
            'quantity_measured': quantity_measured,
            'time_measured': time_measured,
            'time_per_unit': time_per_unit,
            'rate_per_minute': rate_per_minute,
            'cost': cost,
            'approved_rate': None  # Пока нет утверждённой расценки
        })

        # Очистка полей
        self.quantity_measured_input.setValue(0)
        self.time_measured_input.setValue(0.0)

    def update_selected_operation(self):
        """Обновление выбранной операции (стоимость, время 1 детали)"""
        logger.debug("Обновление выбранной операции")
        current_row = self.operations_table.currentRow()
        if current_row >= 0:
            try:
                quantity_measured = int(self.operations_table.item(current_row, 1).text())
                time_measured = float(self.operations_table.item(current_row, 2).text())
                rate_per_minute = float(self.operations_table.item(current_row, 4).text())  # Берём ставку из таблицы

                if quantity_measured == 0:
                    QMessageBox.warning(None, "Ошибка", "Количество по замерам не может быть 0")
                    return

                time_per_unit = time_measured / quantity_measured if quantity_measured != 0 else 0
                cost = time_per_unit * rate_per_minute

                self.operations_table.setItem(current_row, 3, QTableWidgetItem(f"{time_per_unit:.2f}"))
                self.operations_table.setItem(current_row, 5, QTableWidgetItem(f"{cost:.2f}"))

                # Обновляем данные в списке
                if current_row < len(self.operations_data):
                    self.operations_data[current_row]['time_per_unit'] = time_per_unit
                    self.operations_data[current_row]['cost'] = cost
            except (ValueError, AttributeError):
                QMessageBox.warning(None, "Ошибка", "Неверные данные в строке операции")
        else:
            QMessageBox.warning(None, "Ошибка", "Выберите операцию для обновления")

    def delete_selected_operation(self):
        """Удаление выбранной операции из таблицы"""
        logger.debug("Удаление выбранной операции")
        current_row = self.operations_table.currentRow()
        if current_row >= 0:
            # Удаляем строку из таблицы
            self.operations_table.removeRow(current_row)

            # Удаляем соответствующий элемент из списка данных
            if current_row < len(self.operations_data):
                del self.operations_data[current_row]
        else:
            QMessageBox.warning(None, "Ошибка", "Выберите операцию для удаления")

    def add_material(self):
        """Добавление материала"""
        logger.debug("Добавление материала")
        material_name = self.material_combo.currentText()
        material_id = self.material_combo.currentData()

        if not material_name:
            QMessageBox.warning(None, "Ошибка", "Выберите материал")
            return

        # Получаем информацию о материале
        material_info = self.material_manager.get_material_by_id(material_id)
        if not material_info:
            QMessageBox.warning(None, "Ошибка", "Не удалось получить информацию о материале")
            return

        category = material_info[1]

        # Определяем, какой виджет активен
        current_widget_index = self.material_type_widget.currentIndex()

        if current_widget_index == 0:  # Длина и количество (трубы, проволока, профиль)
            length = self.length_input.value()
            quantity = self.quantity_input.value()

            if length <= 0 or quantity <= 0:
                QMessageBox.warning(None, "Ошибка", "Длина и количество должны быть больше 0")
                return

            # Расчет стоимости для труб, проволоки, профиля: длина * вес_1м * количество
            weight_per_meter = material_info[7]  # индекс веса за 1 м
            our_price_per_kg = material_info[13]  # наша цена за кг
            total_weight = length * weight_per_meter * quantity
            cost = total_weight * our_price_per_kg

            # Сохранение данных
            material_data = {
                'material_id': material_id,
                'material_name': material_name,
                'length': length,
                'width': 0,  # для этого типа материалов ширина не используется
                'quantity': quantity,
                'cost': cost,
                'type': 'length_quantity'
            }

        elif current_widget_index == 1:  # Лист (длина, ширина, толщина, количество)
            length = self.length_input_2.value()
            width = self.width_input.value()
            thickness = self.thickness_input.value()
            quantity = self.quantity_input_2.value()

            if length <= 0 or width <= 0 or thickness <= 0 or quantity <= 0:
                QMessageBox.warning(None, "Ошибка", "Все параметры должны быть больше 0")
                return

            # Расчет стоимости для листа: длина * ширина * толщина * плотность * количество * цена_за_кг
            density = 7850  # плотность стали в кг/м3
            volume = length * width * thickness * quantity  # в м3
            weight = volume * density
            our_price_per_kg = material_info[13]  # наша цена за кг
            cost = weight * our_price_per_kg

            # Сохранение данных
            material_data = {
                'material_id': material_id,
                'material_name': material_name,
                'length': length,
                'width': width,
                'thickness': thickness,  # Добавлено thickness
                'quantity': quantity,
                'cost': cost,
                'type': 'dimensions'
            }

        else:  # Только количество (метизы)
            quantity = self.quantity_input_3.value()

            if quantity <= 0:
                QMessageBox.warning(None, "Ошибка", "Количество должно быть больше 0")
                return

            # Расчет стоимости для метизов: цена_за_единицу * количество
            our_price_per_kg = material_info[13]  # наша цена за кг или за штуку
            # В вашем файле для метизов цена указана за штуку, а не за кг
            cost = our_price_per_kg * quantity

            # Сохранение данных
            material_data = {
                'material_id': material_id,
                'material_name': material_name,
                'length': 0,  # для метизов длина не используется
                'width': 0,  # для метизов ширина не используется
                'quantity': quantity,
                'cost': cost,
                'type': 'quantity_only'
            }

        # Добавление в таблицу
        row = self.materials_table.rowCount()
        self.materials_table.insertRow(row)

        self.materials_table.setItem(row, 0, QTableWidgetItem(material_name))
        self.materials_table.setItem(row, 1, QTableWidgetItem(f"{material_data['length']:.3f}"))
        self.materials_table.setItem(row, 2, QTableWidgetItem(f"{material_data['width']:.3f}"))
        self.materials_table.setItem(row, 3, QTableWidgetItem(str(material_data['quantity'])))
        self.materials_table.setItem(row, 4, QTableWidgetItem(f"{material_data['cost']:.2f}"))

        # Сохранение данных
        self.materials_data.append(material_data)

        # Очистка полей в зависимости от типа
        if current_widget_index == 0:
            self.length_input.setValue(0.0)
            self.quantity_input.setValue(0)
        elif current_widget_index == 1:
            self.length_input_2.setValue(0.0)
            self.width_input.setValue(0.0)
            self.thickness_input.setValue(0.0)
            self.quantity_input_2.setValue(0)
        else:
            self.quantity_input_3.setValue(0)

    def update_selected_material(self):
        """Обновление выбранного материала"""
        logger.debug("Обновление выбранного материала")
        current_row = self.materials_table.currentRow()
        if current_row >= 0:
            try:
                # Получаем текущие значения из таблицы
                material_name = self.materials_table.item(current_row, 0).text()
                length = float(self.materials_table.item(current_row, 1).text())
                width = float(self.materials_table.item(current_row, 2).text())
                quantity = int(self.materials_table.item(current_row, 3).text())

                # Найдем ID материала по названию
                material_info = self.material_manager.get_material_by_name(material_name)
                if not material_info:
                    QMessageBox.warning(None, "Ошибка", "Не удалось найти материал для обновления")
                    return

                material_id = material_info[0]
                category = material_info[1]

                # Расчет стоимости в зависимости от типа материала
                if category in ['Труба', 'Проволока', 'Профиль', 'Профиль г/к', 'Прут']:
                    # Расчет стоимости для труб, проволоки, профиля: длина * вес_1м * количество
                    weight_per_meter = material_info[7]  # индекс веса за 1 м
                    our_price_per_kg = material_info[13]  # наша цена за кг
                    total_weight = length * weight_per_meter * quantity
                    cost = total_weight * our_price_per_kg
                elif category == 'Лист':
                    # Расчет стоимости для листа: длина * ширина * толщина * плотность * количество * цена_за_кг
                    thickness = 0.01  # используем среднюю толщину, если не указана
                    density = 7850  # плотность стали в кг/м3
                    volume = length * width * thickness * quantity  # в м3
                    weight = volume * density
                    our_price_per_kg = material_info[13]  # наша цена за кг
                    cost = weight * our_price_per_kg
                else:  # Метизы
                    # Расчет стоимости для метизов: цена_за_единицу * количество
                    our_price_per_kg = material_info[13]  # наша цена за кг или за штуку
                    cost = our_price_per_kg * quantity

                # Обновляем значение стоимости в таблице
                self.materials_table.setItem(current_row, 4, QTableWidgetItem(f"{cost:.2f}"))

                # Обновляем данные в списке
                if current_row < len(self.materials_data):
                    self.materials_data[current_row]['cost'] = cost
            except (ValueError, AttributeError):
                QMessageBox.warning(None, "Ошибка", "Неверные данные в строке материала")
        else:
            QMessageBox.warning(None, "Ошибка", "Выберите материал для обновления")

    def delete_selected_material(self):
        """Удаление выбранного материала из таблицы"""
        logger.debug("Удаление выбранного материала")
        current_row = self.materials_table.currentRow()
        if current_row >= 0:
            # Удаляем строку из таблицы
            self.materials_table.removeRow(current_row)

            # Удаляем соответствующий элемент из списка данных
            if current_row < len(self.materials_data):
                del self.materials_data[current_row]
        else:
            QMessageBox.warning(None, "Ошибка", "Выберите материал для удаления")

    def refresh_products_list(self):
        """Обновление списка изделий"""
        logger.debug("Обновление списка изделий")
        self.products_list.clear()

        products = self.product_manager.get_all_products()
        for product_id, product_id_val, article, name, created_date in products:
            item_text = f"{article} - {name} ({product_id_val})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, product_id)  # Сохраняем ID изделия
            self.products_list.addItem(item)

    def export_selected_product(self):
        """Экспорт выбранного изделия"""
        logger.debug("Экспорт выбранного изделия")
        current_item = self.products_list.currentItem()
        if not current_item:
            QMessageBox.warning(None, "Ошибка", "Выберите изделие для экспорта")
            logger.warning("Попытка экспорта без выбора изделия")
            return

        product_id = current_item.data(Qt.UserRole)
        logger.debug(f"Выбрано изделие ID {product_id} для экспорта")

        # Диалог выбора файла
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Экспорт в Excel",
            f"data/products/{current_item.text()}.xlsx",
            "Excel Files (*.xlsx);;PDF Files (*.pdf)"
        )

        if file_path:
            if file_path.endswith('.xlsx'):
                success = self.report_manager.export_product_to_excel(product_id, file_path)
            elif file_path.endswith('.pdf'):
                success = self.report_manager.export_product_to_pdf(product_id, file_path)
            else:
                success = False

            if success:
                QMessageBox.information(None, "Успех", "Файл успешно экспортирован")
                logger.info("Файл успешно экспортирован в Excel/PDF")
            else:
                QMessageBox.critical(None, "Ошибка", "Ошибка при экспорте")
                logger.error("Ошибка при экспорте в Excel/PDF")

    def get_current_ui_data(self):
        """
        Получает текущие данные из UI для передачи во вкладку "Цена изделия".
        Возвращает словарь с данными изделия, операций и материалов.
        """
        logger.debug("Получение текущих данных из UI для расчета цены")
        try:
            # 1. Общая информация об изделии
            product_info = {
                'product_id': self.product_id_input.text(),
                'article': self.article_input.text(),
                'name': self.name_input.text(),
                'total_weight_kg': 0.0,  # Будет рассчитано позже
                'total_paint_area_m2': 0.0  # Будет рассчитано позже
            }
            logger.debug(f"Общая информация об изделии: {product_info}")

            # 2. Операции
            operations = []
            for row in range(self.operations_table.rowCount()):
                try:
                    operation_data = {
                        'operation_name': self.operations_table.item(row, 0).text() if self.operations_table.item(row,
                                                                                                                  0) else "",
                        'quantity_measured': int(
                            self.operations_table.item(row, 1).text()) if self.operations_table.item(row, 1) else 0,
                        'time_measured': float(self.operations_table.item(row, 2).text()) if self.operations_table.item(
                            row, 2) else 0.0,
                        'time_per_unit': float(self.operations_table.item(row, 3).text()) if self.operations_table.item(
                            row, 3) else 0.0,
                        'rate_per_minute': float(
                            self.operations_table.item(row, 4).text()) if self.operations_table.item(row, 4) else 0.0,
                        'cost': float(self.operations_table.item(row, 5).text()) if self.operations_table.item(row,
                                                                                                               5) else 0.0,
                        'employee_name': self.operations_table.item(row, 6).text() if self.operations_table.item(row,
                                                                                                                 6) else "",
                        'approved_rate': self.operations_table.item(row, 7).text() if self.operations_table.item(row,
                                                                                                                 7) else ""
                    }
                    operations.append(operation_data)
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Ошибка обработки строки операции {row}: {e}")
                    continue  # Пропускаем проблемную строку
            logger.debug(f"Получено {len(operations)} операций из UI")

            # 3. Материалы
            materials = []
            for row in range(self.materials_table.rowCount()):
                try:
                    material_data = {
                        'material_name': self.materials_table.item(row, 0).text() if self.materials_table.item(row,
                                                                                                               0) else "",
                        'length': float(self.materials_table.item(row, 1).text()) if self.materials_table.item(row,
                                                                                                               1) else 0.0,
                        'width': float(self.materials_table.item(row, 2).text()) if self.materials_table.item(row,
                                                                                                              2) else 0.0,
                        'quantity': int(self.materials_table.item(row, 3).text()) if self.materials_table.item(row,
                                                                                                               3) else 0,
                        'cost': float(self.materials_table.item(row, 4).text()) if self.materials_table.item(row,
                                                                                                             4) else 0.0,
                        # Добавим категорию и вес для расчета общей информации
                        'category': "Не определена",  # Пока заглушка
                        'weight_kg': 0.0,  # Пока заглушка
                        'paint_area_m2': 0.0  # Пока заглушка
                    }
                    materials.append(material_data)
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Ошибка обработки строки материала {row}: {e}")
                    continue  # Пропускаем проблемную строку
            logger.debug(f"Получено {len(materials)} материалов из UI")

            ui_data = {
                'product_info': product_info,
                'operations': operations,
                'materials': materials
            }
            logger.debug("Текущие данные из UI успешно получены")
            return ui_data

        except Exception as e:
            logger.error(f"Ошибка при получении данных из UI: {e}", exc_info=True)
            return None

    def show_pricing_for_product(self, product_id):
        """
        Отображает расчет цены для выбранного изделия.
        Вызывается, когда пользователь выбирает изделие в каталоге.
        """
        logger.info(f"Открытие цены для изделия ID {product_id}")
        try:
            if hasattr(self, 'pricing_tab'):
                self.pricing_tab.set_product(product_id)
                # Переключаемся на вкладку "Цена изделия"
                # self.tab_widget.setCurrentWidget(self.pricing_tab)
                # Примечание: self.tab_widget не существует в этом классе,
                # он находится в MainApplication. Логика переключения должна быть там.
                logger.info(f"Цена для изделия ID {product_id} открыта на вкладке 'Цена изделия'")
            else:
                logger.warning("Вкладка 'Цена изделия' не найдена")
        except Exception as e:
            logger.error(f"Ошибка при открытии цены для изделия ID {product_id}: {e}", exc_info=True)
