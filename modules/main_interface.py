# modules/main_interface.py
import logging

import sys
import os

from pathlib import Path

# Автоматически находим путь к плагинам в текущем виртуальном окружении
venv_base = Path(sys.executable).parent.parent  # поднимаемся из Scripts/
plugins_path = venv_base / "Lib" / "site-packages" / "PyQt5" / "Qt5" / "plugins"

if plugins_path.exists():
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins_path)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QLabel, QSpinBox, QDoubleSpinBox, QHeaderView,
    QSplitter, QListWidget, QListWidgetItem, QFrame, QMessageBox, QFileDialog,
    QStackedWidget, QTextEdit, QCheckBox, QApplication, QInputDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from modules.database import DatabaseManager
from modules.materials import MaterialManager
from modules.rates import RateManager
from modules.products import ProductManager
from modules.calculations import CalculationManager
from modules.reports import ReportManager
from modules.interface_pricing import PricingTab
from modules.catalog_table import CatalogTable

logger = logging.getLogger(__name__)


class MainInterface(QWidget):
    # TODO: ДОБАВИТЬ СИГНАЛ ДЛЯ СВЯЗИ МОДУЛЕЙ
    # Сигнал для уведомления о выборе изделия для расчета цены
    product_selected_for_pricing = pyqtSignal(int)

    # TODO: ДОБАВИТЬ СИГНАЛ ДЛЯ ПЕРЕКЛЮЧЕНИЯ НА ВКЛАДКУ ВВОДА ДАННЫХ
    product_selected_for_editing = pyqtSignal(int)

    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
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

        # Создаём вкладку цены сразу
        self.pricing_tab = PricingTab(self.db_manager, self)

        # Инициализация UI компонентов
        self._init_ui_components()

        # Создание вкладок
        self.tab_widget = QTabWidget()
        self.input_tab = self.create_input_tab()
        self.catalog_tab = self.create_catalog_tab()

        self.tab_widget.addTab(self.input_tab, "Ввод данных")
        self.tab_widget.addTab(self.pricing_tab, "Цена изделия")  # Вкладка всегда есть
        self.tab_widget.addTab(self.catalog_tab, "Каталог")

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

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

    def setup_ui(self):
        """Настройка пользовательского интерфейса для QWidget"""
        # Создаем главный layout
        main_layout = QVBoxLayout(self)

        # Создаем виджет вкладок
        self.tab_widget = QTabWidget()

        # Создаем вкладки
        self.input_tab = self.create_input_tab()
        self.catalog_tab = self.create_catalog_tab()

        # Добавляем вкладки
        self.tab_widget.addTab(self.catalog_tab, "Каталог")
        self.tab_widget.addTab(self.input_tab, "Ввод данных")
        # self.pricing_tab = PricingTab(self.db_manager, self)
        # self.tab_widget.addTab(self.pricing_tab, "Цена изделия")



        # Добавляем tab_widget в главный layout
        main_layout.addWidget(self.tab_widget)

        # Устанавливаем layout для виджета
        self.setLayout(main_layout)

    def create_input_tab(self):
        """Создание вкладки ввода данных"""
        logger.debug("Создание вкладки ввода данных")
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Кнопки управления изделием
        control_layout = QHBoxLayout()
        new_product_btn = QPushButton("Новое изделие")
        new_product_btn.clicked.connect(self.clear_form)
        control_layout.addWidget(new_product_btn)
        control_layout.addStretch()
        layout.addLayout(control_layout)

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
        self.product_id_input.setReadOnly(True)  # TODO: СДЕЛАТЬ ID АВТОМАТИЧЕСКИМ И НЕРЕДАКТИРУЕМЫМ
        self.product_id_input.setPlaceholderText("Автоматически присваивается при создании")

        self.article_input = QLineEdit()
        self.name_input = QLineEdit()

        layout.addRow("ID изделия:", self.product_id_input)
        layout.addRow("Артикул:", self.article_input)
        layout.addRow("Название изделия:", self.name_input)

        return group

    def clear_form(self):
        """Очистка формы для создания нового изделия"""
        logger.debug("Очистка формы")
        self.product_id_input.clear()
        self.article_input.clear()
        self.name_input.clear()
        self.operations_table.setRowCount(0)
        self.materials_table.setRowCount(0)
        self.operations_data.clear()
        self.materials_data.clear()
        self.current_product_id = None

    def load_product_to_form(self, product_id):
        """Загрузка изделия в форму для редактирования"""
        logger.info(f"Загрузка изделия ID {product_id} в форму")
        try:
            # Получение информации об изделии
            product_info = self.db_manager.fetch_one(
                "SELECT id, product_id, article, name FROM products WHERE id = ?",
                (product_id,)
            )

            if product_info:
                self.current_product_id = product_info[0]  # Внутренний ID БД
                self.product_id_input.setText(str(product_info[1] if product_info[1] else ""))  # Отображаемый ID
                self.article_input.setText(product_info[2] if product_info[2] else "")
                self.name_input.setText(product_info[3] if product_info[3] else "")

                # Загрузка операций
                self._load_operations_to_form(product_id)

                # Загрузка материалов
                self._load_materials_to_form(product_id)

                logger.info(f"Изделие ID {product_id} загружено в форму")

                # Обновляем статус
                if hasattr(self, 'parent') and hasattr(self.parent(), 'status_bar'):
                    self.parent().status_bar.showMessage(f"Загружено изделие: {product_info[3]}")

            else:
                logger.error(f"Изделие ID {product_id} не найдено в БД")
                QMessageBox.warning(None, "Ошибка", f"Изделие ID {product_id} не найдено")

        except Exception as e:
            logger.error(f"Ошибка при загрузке изделия в форму: {e}", exc_info=True)
            QMessageBox.critical(None, "Ошибка", f"Ошибка при загрузке изделия: {e}")

    def _load_operations_to_form(self, product_id):
        """
        Загружает операции для выбранного изделия в таблицу и создаёт выпадающий список сотрудников.
        """
        logger.debug(f"Загрузка операций для изделия ID={product_id}")
        try:
            query = """
                SELECT id, operation_name, quantity_measured, time_measured, time_per_unit,
                       rate_per_minute, cost, employee_id, approved_rate
                FROM operations
                WHERE product_id = ?
                ORDER BY id
            """
            operations = self.db_manager.fetch_all(query, (product_id,))
            self.operations_table.setRowCount(0)
            self.operations_data = []

            # Подгружаем список сотрудников заранее (для скорости)
            employees = self.db_manager.fetch_all("SELECT id, name FROM employees ORDER BY name")

            for op in operations:
                operation_id, name, qty, t_meas, t_unit, rate, cost, emp_id, appr_rate = op
                row = self.operations_table.rowCount()
                self.operations_table.insertRow(row)

                # Сохраняем операцию в память
                self.operations_data.append({
                    "id": operation_id,
                    "operation_name": name,
                    "quantity_measured": qty,
                    "time_measured": t_meas,
                    "time_per_unit": t_unit,
                    "rate_per_minute": rate,
                    "cost": cost,
                    "employee_id": emp_id,
                    "approved_rate": appr_rate
                })

                # === Заполняем ячейки таблицы ===
                self.operations_table.setItem(row, 0, QTableWidgetItem(name or ""))
                self.operations_table.setItem(row, 1, QTableWidgetItem(str(qty or 0)))
                self.operations_table.setItem(row, 2, QTableWidgetItem(f"{t_meas or 0:.2f}"))
                self.operations_table.setItem(row, 3, QTableWidgetItem(f"{t_unit or 0:.4f}"))
                self.operations_table.setItem(row, 4, QTableWidgetItem(f"{rate or 0:.4f}"))
                self.operations_table.setItem(row, 5, QTableWidgetItem(f"{cost or 0:.2f}"))

                # === Сотрудник — выпадающий список ===
                combo = QComboBox()
                combo.addItem("— Не выбран —", None)
                for emp in employees:
                    combo.addItem(emp[1], emp[0])

                # Устанавливаем текущего сотрудника
                if emp_id:
                    for i in range(combo.count()):
                        if combo.itemData(i) == emp_id:
                            combo.setCurrentIndex(i)
                            break

                combo.currentIndexChanged.connect(
                    lambda index, r=row, cmb=combo: self._on_employee_changed(r, cmb)
                )
                self.operations_table.setCellWidget(row, 6, combo)

                # Утвержденная расценка
                appr_item = QTableWidgetItem(str(appr_rate) if appr_rate is not None else "")
                appr_item.setTextAlignment(Qt.AlignCenter)
                self.operations_table.setItem(row, 7, appr_item)

            logger.info(f"Загружено {len(operations)} операций для изделия {product_id}")

        except Exception as e:
            logger.error(f"Ошибка при загрузке операций: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить операции:\n{e}")

    def _on_employee_changed(self, row, combo):
        """
        Обработчик изменения сотрудника в выпадающем списке таблицы операций.
        Автоматически сохраняет выбор в базу данных и пересчитывает стоимость изделия.
        """
        try:
            operation = self.operations_data[row]
            operation_id = operation["id"]
            new_employee_id = combo.currentData()
            new_employee_name = combo.currentText()

            # Обновляем локальные данные
            self.operations_data[row]["employee_id"] = new_employee_id

            # Обновляем в базе
            query = "UPDATE operations SET employee_id = ? WHERE id = ?"
            self.db_manager.execute_query(query, (new_employee_id, operation_id))
            logger.info(f"Обновлен сотрудник операции {operation_id}: {new_employee_name}")

            # Пересчитываем себестоимость (автоматически)
            from modules.pricing import PricingManager
            pricing = PricingManager(self.db_manager)
            result = pricing.calculate_pricing(self.current_product_id)

            calculated_price = result["cost_indicators"]["calculated_price"]
            approved_price = result["cost_indicators"]["approved_price"]

            if hasattr(self, "pricing_tab") and self.pricing_tab:
                self.pricing_tab.update_price_display(calculated_price, approved_price)

        except Exception as e:
            logger.error(f"Ошибка при обновлении сотрудника в операции: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить сотрудника:\n{e}")

    def _refresh_employee_combos_in_table(self):
        """Обновление всех выпадающих списков сотрудников в таблице"""
        # Загружаем актуальный список сотрудников
        employees = self.db_manager.fetch_all("SELECT id, name FROM employees ORDER BY name")

        # Обновляем каждый комбобокс в таблице
        for row in range(self.operations_table.rowCount()):
            combo = self.operations_table.cellWidget(row, 6)
            if isinstance(combo, QComboBox):
                current_data = combo.currentData()
                combo.clear()
                combo.addItem("Не назначен", None)
                for emp_id, emp_name in employees:
                    combo.addItem(emp_name, emp_id)

                # Восстанавливаем текущее значение
                index = combo.findData(current_data)
                if index >= 0:
                    combo.setCurrentIndex(index)

    def _load_materials_to_form(self, product_id):
        """Загрузка материалов в таблицу"""
        logger.debug(f"Загрузка материалов для изделия ID {product_id}")
        try:
            materials = self.db_manager.fetch_all("""
                SELECT m.name, pm.material_id, pm.length, pm.width, pm.thickness, 
                       pm.quantity, pm.cost, m.category
                FROM product_materials pm
                JOIN materials m ON pm.material_id = m.id
                WHERE pm.product_id = ?
                ORDER BY pm.id
            """, (product_id,))

            self.materials_table.setRowCount(0)
            self.materials_data.clear()

            for mat in materials:
                row = self.materials_table.rowCount()
                self.materials_table.insertRow(row)

                self.materials_table.setItem(row, 0, QTableWidgetItem(mat[0] if mat[0] else ""))
                self.materials_table.setItem(row, 1, QTableWidgetItem(f"{mat[2]:.3f}" if mat[2] else "0.000"))
                self.materials_table.setItem(row, 2, QTableWidgetItem(f"{mat[3]:.3f}" if mat[3] else "0.000"))
                self.materials_table.setItem(row, 3, QTableWidgetItem(str(mat[5]) if mat[5] else "0"))
                self.materials_table.setItem(row, 4, QTableWidgetItem(f"{mat[6]:.2f}" if mat[6] else "0.00"))

                # Определение типа материала для сохранения
                material_type = 'length_quantity'
                if mat[7] == 'Лист':
                    material_type = 'dimensions'
                elif mat[7] == 'Метизы':
                    material_type = 'quantity_only'

                # Сохранение в materials_data
                self.materials_data.append({
                    'material_id': mat[1],
                    'material_name': mat[0],
                    'length': mat[2],
                    'width': mat[3],
                    'thickness': mat[4],
                    'quantity': mat[5],
                    'cost': mat[6],
                    'type': material_type
                })

            logger.debug(f"Загружено {len(materials)} материалов")

        except Exception as e:
            logger.error(f"Ошибка при загрузке материалов: {e}", exc_info=True)

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

        # Выпадающий список сотрудников с возможностью ввода
        employee_layout = QHBoxLayout()
        self.employee_combo = QComboBox()
        self.employee_combo.setEditable(True)  # РЕДАКТИРУЕМЫЙ!
        self.employee_combo.setInsertPolicy(QComboBox.InsertAtTop)

        add_employee_btn = QPushButton("+")
        add_employee_btn.setToolTip("Добавить текущего сотрудника в список")
        add_employee_btn.setFixedWidth(30)
        add_employee_btn.clicked.connect(self.add_current_employee)

        employee_layout.addWidget(QLabel("Сотрудник:"))
        employee_layout.addWidget(self.employee_combo)
        employee_layout.addWidget(add_employee_btn)
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

        # ДОБАВИМ КНОПКУ ДЛЯ СОТРУДНИКОВ
        add_employee_btn = QPushButton("Добавить сотрудника")
        add_employee_btn.clicked.connect(self.add_new_employee_to_table)

        buttons_layout.addWidget(self.add_operation_btn)
        buttons_layout.addWidget(self.update_operation_btn)
        buttons_layout.addWidget(self.delete_operation_btn)
        buttons_layout.addWidget(add_employee_btn)  # ДОБАВИЛИ КНОПКУ
        layout.addLayout(buttons_layout)

        # Таблица с операциями
        self.operations_table = QTableWidget()
        self.operations_table.setColumnCount(8)

        # ЗАГОЛОВКИ В ДВА РЯДА
        self.operations_table.setHorizontalHeaderLabels([
            "Операция",
            "Кол-во\nпо замерам",
            "Время\nзамера (мин)",
            "Время на\n1 деталь (мин)",
            "Ставка\n(грн/мин)",
            "Стоимость\n(грн)",
            "Сотрудник",  # ЭТА ЯЧЕЙКА БУДЕТ ВЫПАДАЮЩИМ СПИСКОМ
            "Утверждённая\nрасценка"
        ])

        # Настраиваем высоту заголовков для двустрочного текста
        header = self.operations_table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setSectionResizeMode(QHeaderView.Stretch)

        # Увеличиваем высоту заголовка для двустрочного текста
        self.operations_table.horizontalHeader().setFixedHeight(50)

        # Разрешаем редактирование утвержденной цены
        self.operations_table.setEditTriggers(QTableWidget.AllEditTriggers)

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
        """Создание вкладки каталога с улучшенным функционалом"""
        logger.debug("Создание вкладки каталога")

        # Используем готовый виджет CatalogTable
        self.catalog_table = CatalogTable(self.db_manager, self)

        # Подключаем сигналы
        self.catalog_table.product_selected.connect(self.on_catalog_product_selected)
        self.catalog_table.product_deleted.connect(self.on_catalog_product_deleted)
        self.catalog_table.catalog_updated.connect(self.on_catalog_updated)
        self.catalog_table.product_edit_requested.connect(self.on_catalog_edit_requested)  # ДОБАВЛЯЕМ

        return self.catalog_table

    def on_catalog_product_selected(self, product_id):
        """Обработка двойного клика — открыть вкладку 'Цена изделия'"""
        try:
            product = self.db_manager.fetch_one("SELECT id FROM products WHERE id = ?", (product_id,))
            if not product:
                QMessageBox.warning(self, "Ошибка", "Изделие не найдено в базе данных")
                return
            # Отправляем сигнал — переключение делает MainApplication
            self.product_selected_for_pricing.emit(product_id)
        except Exception as e:
            logger.error(f"Ошибка при выборе изделия: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке изделия: {e}")

    def on_catalog_product_deleted(self, product_id):
        """Сброс данных при удалении изделия из каталога"""
        if self.current_product_id == product_id:
            self.clear_form()
        # Также можно обновить каталог, но это уже делает CatalogTable

    def on_catalog_updated(self):
        """Обработка обновления каталога"""
        logger.debug("Каталог обновлен")
        # Обновляем другие компоненты при необходимости

    def update_catalog_prices(self, product_id, approved_price, calculated_price):
        """Обновление цен в каталоге при изменении в PricingTab"""
        if hasattr(self, 'catalog_table'):
            self.catalog_table.update_product_price(product_id, approved_price, calculated_price)

    def load_initial_data(self):
        """Загрузка начальных данных"""
        logger.debug("Загрузка начальных данных")

        # ПРОВЕРЯЕМ СОТРУДНИКОВ
        if not self.check_employees_loaded():
            logger.warning("Сотрудники не загружены!")
            QMessageBox.warning(None, "Внимание",
                                "Сотрудники не загружены из Excel файла.\n"
                                "Убедитесь что файл data/employees.xlsx существует\n"
                                "и содержит лист 'Сотрудники' с ФИО в первом столбце.")

        # Подключение сигналов для операций и материалов
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        self.material_combo.currentIndexChanged.connect(self.on_material_changed)
        self.add_operation_btn.clicked.connect(self.add_operation)
        self.update_operation_btn.clicked.connect(self.update_selected_operation)
        self.delete_operation_btn.clicked.connect(self.delete_selected_operation)
        self.add_material_btn.clicked.connect(self.add_material)
        self.update_material_btn.clicked.connect(self.update_selected_material)
        self.delete_material_btn.clicked.connect(self.delete_selected_material)

        # Загрузка операций и материалов в комбобоксы
        self.load_operations_to_combo()
        self.load_employees_to_combo()  # ЗАГРУЖАЕМ СОТРУДНИКОВ
        self.load_categories_to_combo()

        # Загрузка списка изделий через новый каталог
        if hasattr(self, 'catalog_tab') and hasattr(self.catalog_tab, 'refresh_catalog'):
            self.catalog_tab.refresh_catalog()

    def on_product_selected_for_editing(self, product_id):
        """Обработчик выбора изделия для редактирования"""
        logger.info(f"Выбрано изделие для редактирования ID {product_id}")
        try:
            # Загружаем изделие в форму
            self.load_product_to_form(product_id)

            # Переключаемся на вкладку ввода данных
            if hasattr(self, 'parent') and hasattr(self.parent(), 'tab_widget'):
                self.parent().tab_widget.setCurrentIndex(0)  # Вкладка "Ввод данных"

        except Exception as e:
            logger.error(f"Ошибка при загрузке изделия для редактирования: {e}", exc_info=True)
            QMessageBox.critical(None, "Ошибка", f"Ошибка при загрузке изделия: {e}")

    def on_product_selected_for_pricing(self, product_id):
        """Обработчик выбора изделия для расчета цены"""
        logger.info(f"Выбрано изделие для расчета цены ID {product_id}")
        try:
            # Устанавливаем изделие во вкладке цены
            if hasattr(self, 'pricing_tab'):
                self.pricing_tab.set_product(product_id)

            # Переключаемся на вкладку цены
            if hasattr(self, 'parent') and hasattr(self.parent(), 'tab_widget'):
                self.parent().tab_widget.setCurrentIndex(2)  # Вкладка "Цена изделия"

        except Exception as e:
            logger.error(f"Ошибка при открытии цены изделия: {e}", exc_info=True)
            QMessageBox.critical(None, "Ошибка", f"Ошибка при открытии цены: {e}")

    def on_edit_clicked(self):
        """Обработка нажатия кнопки 'Редактирование'"""
        try:
            current_item = self.products_list.currentItem()
            if not current_item:
                QMessageBox.warning(None, "Ошибка", "Выберите изделие для редактирования")
                logger.warning("Попытка редактирования без выбора изделия")
                return

            product_id = current_item.data(Qt.UserRole)
            logger.info(f"Редактирование изделия ID {product_id}")

            # Загружаем изделие в форму
            self.load_product_to_form(product_id)

            # Испускаем сигнал для переключения на вкладку ввода данных
            self.product_selected_for_editing.emit(product_id)

            logger.info(f"Изделие ID {product_id} загружено для редактирования")

        except Exception as e:
            logger.error(f"Ошибка при редактировании изделия: {e}", exc_info=True)
            QMessageBox.critical(None, "Ошибка", f"Ошибка при загрузке изделия: {e}")

    def load_initial_data(self):
        """Загрузка начальных данных"""
        logger.debug("Загрузка начальных данных")

        # Подключение сигналов для операций и материалов
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        self.material_combo.currentIndexChanged.connect(self.on_material_changed)
        self.add_operation_btn.clicked.connect(self.add_operation)
        self.update_operation_btn.clicked.connect(self.update_selected_operation)
        self.delete_operation_btn.clicked.connect(self.delete_selected_operation)
        self.add_material_btn.clicked.connect(self.add_material)
        self.update_material_btn.clicked.connect(self.update_selected_material)
        self.delete_material_btn.clicked.connect(self.delete_selected_material)

        # УДАЛЯЕМ старые подключения кнопок каталога
        # self.refresh_btn.clicked.connect(self.refresh_products_list)
        # self.export_btn.clicked.connect(self.export_selected_product)

        # Загрузка операций и материалов в комбобоксы
        self.load_operations_to_combo()
        self.load_employees_to_combo()
        self.load_categories_to_combo()

        # Загрузка списка изделий через новый каталог
        if hasattr(self, 'catalog_tab') and hasattr(self.catalog_tab, 'refresh_catalog'):
            self.catalog_tab.refresh_catalog()

    def load_employees_to_combo(self):
        """Загрузка сотрудников в комбобокс — ФИО в одном поле"""
        logger.debug("Загрузка сотрудников в комбобокс")
        try:
            # Берём только id и name (ФИО целиком)
            query = "SELECT id, name FROM employees ORDER BY name"
            employees = self.db_manager.fetch_all(query)
            logger.debug(f"Найдено сотрудников в БД: {len(employees)}")

            self.employee_combo.clear()
            self.employee_combo.addItem("Не назначен", None)
            for emp_id, full_name in employees:
                self.employee_combo.addItem(full_name.strip(), emp_id)
                logger.debug(f"Добавлен сотрудник: {full_name} (ID: {emp_id})")

            if not employees:
                logger.warning("В БД нет сотрудников!")
                QMessageBox.warning(None, "Внимание",
                                    "Сотрудники не загружены. Используйте меню 'Справочники → Список сотрудников'.")

        except Exception as e:
            logger.error(f"Ошибка при загрузке сотрудников: {e}", exc_info=True)
            QMessageBox.critical(None, "Ошибка", f"Не удалось загрузить список сотрудников:\n{e}")

    def on_catalog_edit_requested(self, product_id):
        """Обработка запроса на редактирование изделия из каталога"""
        logger.info(f"Запрос на редактирование изделия ID {product_id}")
        # Просто отправляем сигнал — переключение делает MainApplication
        self.product_selected_for_editing.emit(product_id)

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
        employee_id = self.employee_combo.currentData()
        employee_name = self.employee_combo.currentText()
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
        self.operations_table.setItem(row, 3, QTableWidgetItem(f"{time_per_unit:.4f}"))
        self.operations_table.setItem(row, 4, QTableWidgetItem(f"{rate_per_minute:.4f}"))
        self.operations_table.setItem(row, 5, QTableWidgetItem(f"{cost:.2f}"))
        self.operations_table.setItem(row, 6, QTableWidgetItem(employee_name))

        # TODO: ДОБАВИТЬ ПОЛЕ ДЛЯ УТВЕРЖДЕННОЙ ЦЕНЫ (ПУСТОЕ ПО УМОЛЧАНИЮ)
        approved_rate_item = QTableWidgetItem("")
        approved_rate_item.setTextAlignment(Qt.AlignCenter)
        self.operations_table.setItem(row, 7, approved_rate_item)

        # Сохранение данных - ОБНОВЛЕНО: сохраняем employee_id
        self.operations_data.append({
            'operation_name': operation_name,
            'employee_id': employee_id,  # СОХРАНЯЕМ ID сотрудника
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
        """
        Обновляет выбранную операцию:
         - вычисляет time_per_unit и cost (с учётом approved_rate),
         - обновляет GUI,
         - обновляет запись в БД по operations.id (с fallback-поиском id),
         - обновляет self.operations_data,
         - перезагружает таблицу операций для актуальности.
        """
        logger.debug("Обновление выбранной операции (start)")
        current_row = self.operations_table.currentRow()

        if current_row < 0:
            QMessageBox.warning(None, "Ошибка", "Выберите операцию для обновления")
            return

        try:
            # Получаем выбранного сотрудника
            current_employee_id = self.employee_combo.currentData()
            current_employee_name = self.employee_combo.currentText()
            logger.debug(f"Выбран сотрудник: {current_employee_name} (ID={current_employee_id})")

            # Берём значения из таблицы (защищённо)
            def _get_item_text(r, c, default=""):
                item = self.operations_table.item(r, c)
                return item.text().strip() if item and item.text() is not None else default

            operation_name = _get_item_text(current_row, 0, "")
            quantity_str = _get_item_text(current_row, 1, "0")
            time_str = _get_item_text(current_row, 2, "0")
            rate_str = _get_item_text(current_row, 4, "0")
            approved_str = _get_item_text(current_row, 7, "")

            # Парсинг чисел (используем существующий парсер если есть)
            try:
                quantity_measured = int(self._parse_decimal_value(quantity_str))
            except Exception:
                quantity_measured = int(float(quantity_str)) if quantity_str else 0

            try:
                time_measured = float(self._parse_decimal_value(time_str))
            except Exception:
                time_measured = float(time_str) if time_str else 0.0

            try:
                rate_per_minute = float(self._parse_decimal_value(rate_str))
            except Exception:
                rate_per_minute = float(rate_str) if rate_str else 0.0

            # Валидация
            if quantity_measured <= 0:
                QMessageBox.warning(None, "Ошибка", "Количество по замерам должно быть больше 0")
                return

            time_per_unit = time_measured / quantity_measured if quantity_measured else 0.0

            # Рассчитываем cost: если есть approved_rate — используем её (как абсолютную сумму),
            # иначе считаем time_per_unit * rate_per_minute
            cost = None
            if approved_str:
                try:
                    cost = float(self._parse_decimal_value(approved_str))
                    logger.debug(f"Используется утверждённая расценка: {cost}")
                except Exception:
                    cost = time_per_unit * rate_per_minute
                    logger.warning("Неверная утверждённая расценка — использована расчетная")
            else:
                cost = time_per_unit * rate_per_minute

            # Обновляем GUI ячейки
            self.operations_table.setItem(current_row, 3, QTableWidgetItem(f"{time_per_unit:.4f}"))
            self.operations_table.setItem(current_row, 5, QTableWidgetItem(f"{cost:.2f}"))
            self.operations_table.setItem(current_row, 6, QTableWidgetItem(current_employee_name))

            # Обновляем запись в self.operations_data (если есть)
            if current_row < len(self.operations_data):
                op_data = self.operations_data[current_row]
            else:
                op_data = None

            # Определяем operation_id — предпочитаем из op_data, иначе попробуем найти в БД (fallback)
            operation_id = None
            if op_data:
                operation_id = op_data.get("id")

            if not operation_id and self.current_product_id and operation_name:
                # fallback: искать id по product_id + operation_name (на случай, если id не загружен)
                try:
                    find_q = "SELECT id FROM operations WHERE product_id = ? AND operation_name = ? LIMIT 1"
                    found = self.db_manager.fetch_one(find_q, (self.current_product_id, operation_name))
                    if found:
                        operation_id = found[0]
                        logger.debug(f"Fallback: найден operation_id={operation_id} по имени операции")
                except Exception:
                    logger.exception("Ошибка при попытке найти operation_id по имени операции")

            # Если у нас нет id — создаём новую запись (INSERT) или предупреждаем
            if not operation_id:
                # Если по логике проекта ожидается, что операции уже есть в БД,
                # то лучше сообщить о проблеме, чем молча пропускать.
                logger.warning(
                    f"Не найден id операции для строки {current_row} (operation='{operation_name}'). Попытка вставки новой записи.")
                if self.current_product_id:
                    insert_q = """
                        INSERT INTO operations
                        (product_id, operation_name, quantity_measured, time_measured,
                         time_per_unit, rate_per_minute, cost, employee_id, approved_rate)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    params = (
                        self.current_product_id,
                        operation_name,
                        quantity_measured,
                        time_measured,
                        time_per_unit,
                        rate_per_minute,
                        cost,
                        current_employee_id,
                        approved_str or None
                    )
                    self.db_manager.execute_query(insert_q, params)
                    # Получим id последней вставки
                    try:
                        new_id_row = self.db_manager.fetch_one("SELECT last_insert_rowid()")
                        if new_id_row:
                            operation_id = new_id_row[0]
                            logger.info(f"Вставлена новая операция id={operation_id}")
                    except Exception:
                        logger.exception("Не удалось получить last_insert_rowid() после вставки операции")

            # Если у нас есть id — обновляем по id
            if operation_id:
                update_q = """
                    UPDATE operations
                    SET quantity_measured = ?, time_measured = ?, time_per_unit = ?, 
                        rate_per_minute = ?, cost = ?, employee_id = ?, approved_rate = ?
                    WHERE id = ?
                """
                params = (
                    quantity_measured, time_measured, time_per_unit,
                    rate_per_minute, cost, current_employee_id, approved_str or None, operation_id
                )
                self.db_manager.execute_query(update_q, params)
                logger.info(f"Операция id={operation_id} обновлена: cost={cost}, employee_id={current_employee_id}")

                # Обновляем op_data в памяти (если было)
                if op_data is not None:
                    op_data.update({
                        "id": operation_id,
                        "operation_name": operation_name,
                        "quantity_measured": quantity_measured,
                        "time_measured": time_measured,
                        "time_per_unit": time_per_unit,
                        "rate_per_minute": rate_per_minute,
                        "cost": cost,
                        "employee_id": current_employee_id,
                        "employee_name": current_employee_name,
                        "approved_rate": approved_str or None
                    })
            else:
                logger.error("Не удалось получить или создать id операции — изменения не записаны в БД")
                QMessageBox.warning(None, "Внимание", "Не удалось сохранить операцию в базе данных.")

            # После успешного обновления перезагружаем операции из БД, чтобы гарантировать консистентность
            if self.current_product_id:
                self._load_operations_to_form(self.current_product_id)

            QMessageBox.information(None, "Успех", "Операция успешно обновлена")

        except Exception as e:
            logger.error(f"Ошибка при обновлении операции: {e}", exc_info=True)
            QMessageBox.critical(None, "Ошибка", f"Не удалось обновить операцию:\n{e}")

        try:
            from modules.pricing import PricingManager
            pricing = PricingManager(self.db_manager)
            result = pricing.calculate_pricing(self.current_product_id)

            calculated_price = result["cost_indicators"]["calculated_price"]
            approved_price = result["cost_indicators"]["approved_price"]

            # Если вкладка "Цена изделия" уже открыта — обновим её визуально
            if hasattr(self, "pricing_tab") and self.pricing_tab:
                self.pricing_tab.update_price_display(calculated_price, approved_price)

            logger.info(f"Автоматический пересчет цены изделия {self.current_product_id}: {calculated_price:.2f}")
        except Exception as e:
            logger.error(f"Ошибка при автоматическом пересчете себестоимости: {e}", exc_info=True)

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

    def load_operations_for_product(self, product_id: int):
        """Загружает операции из базы данных и отображает их в таблице."""
        try:
            query = """
                SELECT id, operation_name, quantity_measured, time_measured,
                       time_per_unit, rate_per_minute, cost, employee_id, approved_rate
                FROM operations
                WHERE product_id = ?
            """
            operations = self.db_manager.fetch_all(query, (product_id,))

            self.operations_data = []
            self.operations_table.setRowCount(0)

            for op in operations:
                (
                    operation_id, operation_name, quantity_measured, time_measured,
                    time_per_unit, rate_per_minute, cost, employee_id, approved_rate
                ) = op

                # Имя сотрудника
                employee_name = self.db_manager.fetch_value(
                    "SELECT name FROM employees WHERE id = ?", (employee_id,)
                ) or ""

                self.operations_data.append({
                    "id": operation_id,
                    "operation_name": operation_name,
                    "quantity_measured": quantity_measured,
                    "time_measured": time_measured,
                    "time_per_unit": time_per_unit,
                    "rate_per_minute": rate_per_minute,
                    "cost": cost,
                    "employee_id": employee_id,
                    "employee_name": employee_name,
                    "approved_rate": approved_rate,
                })

                # Добавляем строку в таблицу
                row = self.operations_table.rowCount()
                self.operations_table.insertRow(row)
                self.operations_table.setItem(row, 0, QTableWidgetItem(operation_name))
                self.operations_table.setItem(row, 1, QTableWidgetItem(str(quantity_measured)))
                self.operations_table.setItem(row, 2, QTableWidgetItem(str(time_measured)))
                self.operations_table.setItem(row, 3, QTableWidgetItem(f"{time_per_unit:.4f}"))
                self.operations_table.setItem(row, 4, QTableWidgetItem(str(rate_per_minute)))
                self.operations_table.setItem(row, 5, QTableWidgetItem(f"{cost:.2f}"))
                self.operations_table.setItem(row, 6, QTableWidgetItem(employee_name))
                self.operations_table.setItem(row, 7, QTableWidgetItem(str(approved_rate or "")))

            logger.info(f"Загружено {len(self.operations_data)} операций для изделия ID={product_id}")

        except Exception as e:
            logger.error(f"Ошибка при загрузке операций: {e}", exc_info=True)
            QMessageBox.critical(None, "Ошибка", f"Не удалось загрузить операции:\n{e}")

    def update_selected_material(self):
        """Обновление выбранного материала — с сохранением в БД"""
        logger.debug("Обновление выбранного материала")
        current_row = self.materials_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(None, "Ошибка", "Выберите материал для обновления")
            return

        try:
            # Получаем текущие значения из таблицы
            material_name = self.materials_table.item(current_row, 0).text()
            length_str = self.materials_table.item(current_row, 1).text()
            width_str = self.materials_table.item(current_row, 2).text()
            quantity_str = self.materials_table.item(current_row, 3).text()
            cost_str = self.materials_table.item(current_row, 4).text()

            length = float(length_str) if length_str else 0.0
            width = float(width_str) if width_str else 0.0
            quantity = int(quantity_str) if quantity_str else 0

            # Находим material_id
            material_info = self.material_manager.get_material_by_name(material_name)
            if not material_info:
                QMessageBox.warning(None, "Ошибка", "Материал не найден в справочнике")
                return
            material_id = material_info[0]
            our_price_per_kg = material_info[13]

            category = material_info[1]
            if category in ['Труба', 'Проволока', 'Профиль', 'Профиль г/к', 'Прут']:
                weight_per_meter = material_info[7]
                total_weight = length * weight_per_meter * quantity
                cost = total_weight * our_price_per_kg
            elif category == 'Лист':
                thickness = self.materials_data[current_row].get('thickness', 0.01)  # берём из памяти!
                density = 7850
                volume = length * width * thickness * quantity
                weight = volume * density
                cost = weight * our_price_per_kg
            else:  # Метизы
                cost = our_price_per_kg * quantity

            # === СРАЗУ СОХРАНЯЕМ В БД ===
            if self.current_product_id and current_row < len(self.materials_data):
                mat_data = self.materials_data[current_row]
                update_query = """
                    UPDATE product_materials
                    SET length = ?, width = ?, thickness = ?, quantity = ?, cost = ?
                    WHERE product_id = ? AND material_id = ?
                """
                params = (
                    length, width, mat_data.get('thickness', 0.0), quantity, cost,
                    self.current_product_id, material_id
                )
                self.db_manager.execute_query(update_query, params)
                logger.info(f"Материал '{material_name}' обновлён в БД")

            # Обновляем GUI
            self.materials_table.setItem(current_row, 4, QTableWidgetItem(f"{cost:.2f}"))

            # Обновляем в памяти
            if current_row < len(self.materials_data):
                self.materials_data[current_row]['cost'] = cost
                self.materials_data[current_row]['length'] = length
                self.materials_data[current_row]['width'] = width
                self.materials_data[current_row]['quantity'] = quantity

            # Автоматический пересчёт цены
            from modules.pricing import PricingManager
            pricing = PricingManager(self.db_manager)
            result = pricing.calculate_pricing(self.current_product_id)
            calculated_price = result["cost_indicators"]["calculated_price"]
            approved_price = result["cost_indicators"]["approved_price"]
            if hasattr(self, "pricing_tab") and self.pricing_tab:
                self.pricing_tab.update_price_display(calculated_price, approved_price)

            QMessageBox.information(None, "Успех", "Материал обновлён")

        except Exception as e:
            logger.error(f"Ошибка при обновлении материала: {e}", exc_info=True)
            QMessageBox.critical(None, "Ошибка", f"Не удалось обновить материал:\n{e}")

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

        # Обновим метод обновления списка изделий
        def refresh_products_list(self):
            """Обновление списка изделий в каталоге"""
            logger.debug("Обновление списка изделий в каталоге")
            if hasattr(self, 'catalog_tab') and hasattr(self.catalog_tab, 'refresh_catalog'):
                self.catalog_tab.refresh_catalog()

    def export_selected_product(self):
        """Экспорт выбранного изделия"""
        logger.debug("Экспорт выбранного изделия")
        current_item = self.products_list.currentItem()
        if not current_item:
            QMessageBox.warning(None, "Ошибка", "Выберите изделие для экспорта")
            logger.warning("Попытка экспорта без выбора изделия")
            return

        product_id = current_item.data(Qt.UserRole)

        # Диалог выбора файла
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Сохранить изделие",
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
                QMessageBox.information(None, "Успех", "Файл успешно сохранен")
                logger.info("Файл успешно сохранен")
            else:
                QMessageBox.critical(None, "Ошибка", "Ошибка при сохранении файла")
                logger.error("Ошибка при сохранении файла")

    def on_product_double_clicked(self, item):
        """Обработка двойного клика по изделию в каталоге"""
        try:
            product_id = item.data(Qt.UserRole)
            logger.info(f"Двойной клик по изделию ID {product_id}")
            self.show_pricing_for_product(product_id)
        except Exception as e:
            logger.error(f"Ошибка при обработке двойного клика: {e}", exc_info=True)

    def show_pricing_for_product(self, product_id):
        """
        Отображает расчет цены для выбранного изделия.
        Вызывается, когда пользователь выбирает изделие в каталоге.
        """
        logger.info(f"Открытие цены для изделия ID {product_id}")
        try:
            if hasattr(self, 'pricing_tab'):
                # Устанавливаем изделие во вкладке цены
                self.pricing_tab.set_product(product_id)
                # Испускаем сигнал для переключения вкладки
                self.product_selected_for_pricing.emit(product_id)
                logger.info(f"Цена для изделия ID {product_id} открыта на вкладке 'Цена изделия'")
            else:
                logger.warning("Вкладка 'Цена изделия' не найдена")
        except Exception as e:
            logger.error(f"Ошибка при открытии цены для изделия ID {product_id}: {e}", exc_info=True)

    def _parse_decimal_value(self, value_str):
        """Парсинг десятичного числа с обработкой разных разделителей"""
        if not value_str:
            return 0.0

        try:
            # Заменяем запятую на точку и убираем лишние пробелы
            normalized_str = str(value_str).strip().replace(',', '.')

            # Убираем все символы, кроме цифр, точки и минуса
            cleaned_str = ''.join(c for c in normalized_str if c.isdigit() or c in ['.', '-'])

            if not cleaned_str:
                return 0.0

            return float(cleaned_str)
        except (ValueError, TypeError):
            logger.warning(f"Не удалось преобразовать значение '{value_str}' в число")
            return 0.0

    def check_employees_loaded(self):
        """Проверка загрузки сотрудников"""
        logger.debug("Проверка загрузки сотрудников")
        try:
            employees = self.db_manager.fetch_all("SELECT id, name FROM employees ORDER BY name")
            logger.debug(f"Сотрудников в БД: {len(employees)}")

            for emp_id, emp_name in employees:
                logger.debug(f"Сотрудник: ID={emp_id}, Name='{emp_name}'")

            return len(employees) > 0
        except Exception as e:
            logger.error(f"Ошибка при проверке сотрудников: {e}")
            return False

    def add_new_employee(self):
        """Добавление нового сотрудника"""
        employee_name, ok = QInputDialog.getText(
            None,
            "Добавить сотрудника",
            "Введите ФИО нового сотрудника:"
        )

        if ok and employee_name.strip():
            try:
                # Добавляем в БД
                query = "INSERT INTO employees (name) VALUES (?)"
                self.db_manager.execute_query(query, (employee_name.strip(),))

                # Обновляем комбобокс
                self.load_employees_to_combo()

                # Выбираем нового сотрудника
                index = self.employee_combo.findText(employee_name.strip())
                if index >= 0:
                    self.employee_combo.setCurrentIndex(index)

                QMessageBox.information(None, "Успех", "Сотрудник добавлен")
                logger.info(f"Добавлен новый сотрудник: {employee_name}")

            except Exception as e:
                logger.error(f"Ошибка при добавлении сотрудника: {e}")
                QMessageBox.critical(None, "Ошибка", f"Ошибка при добавлении сотрудника: {e}")

    def add_current_employee(self):
        """Добавление текущего сотрудника из поля ввода"""
        employee_name = self.employee_combo.currentText().strip()

        if employee_name and employee_name != "Не назначен":
            try:
                # Проверяем, есть ли уже такой сотрудник
                existing = self.db_manager.fetch_one(
                    "SELECT id FROM employees WHERE name = ?",
                    (employee_name,)
                )

                if not existing:
                    # Добавляем в БД
                    query = "INSERT INTO employees (name) VALUES (?)"
                    self.db_manager.execute_query(query, (employee_name,))

                    # Обновляем комбобокс
                    self.load_employees_to_combo()

                    logger.info(f"Добавлен новый сотрудник: {employee_name}")
                    QMessageBox.information(None, "Успех", "Сотрудник добавлен в список")
                else:
                    QMessageBox.information(None, "Информация", "Такой сотрудник уже есть в списке")

            except Exception as e:
                logger.error(f"Ошибка при добавлении сотрудника: {e}")
                QMessageBox.critical(None, "Ошибка", f"Ошибка при добавлении сотрудника: {e}")

    def add_new_employee_to_table(self):
        """Добавление нового сотрудника через диалог"""
        employee_name, ok = QInputDialog.getText(
            None,
            "Добавить сотрудника",
            "Введите ФИО нового сотрудника:"
        )

        if ok and employee_name.strip():
            try:
                # ПРОВЕРКА НА ДУБЛИКАТ
                existing_employee = self.db_manager.fetch_one(
                    "SELECT id FROM employees WHERE name = ?",
                    (employee_name.strip(),)
                )

                if existing_employee:
                    reply = QMessageBox.question(
                        None,
                        "Сотрудник уже существует",
                        f"Сотрудник '{employee_name}' уже есть в списке.\nХотите добавить другого сотрудника?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        self.add_new_employee_to_table()  # Рекурсивный вызов
                    return

                # Добавляем в БД
                query = "INSERT INTO employees (name) VALUES (?)"
                self.db_manager.execute_query(query, (employee_name.strip(),))

                # ОБНОВЛЯЕМ ВСЕ ВЫПАДАЮЩИЕ СПИСКИ
                self._refresh_employee_combos_in_table()
                self.load_employees_to_combo()  # ОБНОВЛЯЕМ ОСНОВНОЙ КОМБОБОКС

                QMessageBox.information(None, "Успех", "Сотрудник добавлен")
                logger.info(f"Добавлен новый сотрудник: {employee_name}")

            except Exception as e:
                logger.error(f"Ошибка при добавлении сотрудника: {e}")
                QMessageBox.critical(None, "Ошибка", f"Ошибка при добавлении сотрудника: {e}")

    def _refresh_employee_combos_in_table(self):
        """Обновление всех выпадающих списков сотрудников в таблице"""
        # Загружаем актуальный список сотрудников
        employees = self.db_manager.fetch_all("SELECT id, name FROM employees ORDER BY name")

        # Обновляем каждый комбобокс в таблице
        for row in range(self.operations_table.rowCount()):
            combo = self.operations_table.cellWidget(row, 6)
            if isinstance(combo, QComboBox):
                current_data = combo.currentData()
                combo.clear()
                combo.addItem("Не назначен", None)
                for emp_id, emp_name in employees:
                    combo.addItem(emp_name, emp_id)

                # Восстанавливаем текущее значение
                index = combo.findData(current_data)
                if index >= 0:
                    combo.setCurrentIndex(index)

        # И ЭТОТ МЕТОД ТОЖЕ В КЛАСС MainInterface:

    def _on_employee_changed(self, row, combo):
        """
        Обработчик изменения сотрудника в выпадающем списке таблицы операций.
        Автоматически сохраняет выбор в базу данных и пересчитывает стоимость изделия.
        """
        try:
            operation = self.operations_data[row]
            operation_id = operation["id"]

            # Получаем ID и имя сотрудника из выпадающего списка
            new_employee_id = combo.currentData()  # ✅ исправлено
            new_employee_name = combo.currentText()

            logger.debug(f"Изменен сотрудник в строке {row} на ID: {new_employee_id} ({new_employee_name})")

            # Обновляем данные в памяти
            self.operations_data[row]["employee_id"] = new_employee_id

            # Обновляем в базе
            query = "UPDATE operations SET employee_id = ? WHERE id = ?"
            self.db_manager.execute_query(query, (new_employee_id, operation_id))
            logger.info(f"Обновлен сотрудник для операции ID={operation_id}: {new_employee_name}")

            # После изменения — пересчет себестоимости
            from modules.pricing import PricingManager
            pricing = PricingManager(self.db_manager)
            result = pricing.calculate_pricing(self.current_product_id)

            calculated_price = result["cost_indicators"]["calculated_price"]
            approved_price = result["cost_indicators"]["approved_price"]

            # Обновляем вкладку "Цена изделия", если она есть
            if hasattr(self, "pricing_tab") and self.pricing_tab:
                self.pricing_tab.update_price_display(calculated_price, approved_price)

        except Exception as e:
            logger.error(f"Ошибка при обновлении сотрудника в операции: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить сотрудника:\n{e}")
