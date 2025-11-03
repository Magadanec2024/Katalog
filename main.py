# main.py
import sys
import os

from pathlib import Path

# Автоматически находим путь к плагинам в текущем виртуальном окружении
venv_base = Path(sys.executable).parent.parent  # поднимаемся из Scripts/
plugins_path = venv_base / "Lib" / "site-packages" / "PyQt5" / "Qt5" / "plugins"

if plugins_path.exists():
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins_path)

import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QStatusBar, QMenuBar, \
    QMessageBox, QFileDialog
from PyQt5.QtCore import Qt



# Настройка логгирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info("=" * 50)
logger.info("ЗАПУСК ГЛАВНОГО ПРИЛОЖЕНИЯ")
logger.info("=" * 50)

# Импорты модулей приложения
try:
    from modules.database import DatabaseManager
    from modules.main_interface import MainInterface

    logger.debug("Модули базы данных и интерфейса импортированы успешно")
except ImportError as e:
    logger.critical(f"Критическая ошибка импорта модулей: {e}", exc_info=True)
    QMessageBox.critical(None, "Ошибка импорта", f"Не удалось импортировать необходимые модули: {e}")
    sys.exit(1)

    # Проверка и добавление колонки calculated_price, если её нет
def ensure_calculated_price_column(db_manager: DatabaseManager):
    try:
        # Проверим, существует ли колонка
        db_manager.execute_query("SELECT calculated_price FROM products LIMIT 1")
        logger.info("Колонка 'calculated_price' уже существует в таблице products")
    except Exception as e:
        if "no such column: calculated_price" in str(e):
            logger.info("Колонка 'calculated_price' отсутствует. Добавляем...")
            db_manager.execute_query("ALTER TABLE products ADD COLUMN calculated_price REAL")
            logger.info("Колонка 'calculated_price' успешно добавлена")
        else:
            logger.error(f"Неожиданная ошибка при проверке колонки: {e}")
            raise

class MainApplication(QMainWindow):
    """Главная форма приложения"""

    def __init__(self):
        super().__init__()
        logger.info("Инициализация главного приложения")
        self.setWindowTitle("Программа расчета стоимости изделий")
        self.setGeometry(100, 100, 1400, 900)

        # Инициализация базы данных
        try:
            self.db_manager = DatabaseManager()
            logger.debug("Менеджер базы данных инициализирован")
        except Exception as e:
            logger.critical(f"Критическая ошибка при инициализации базы данных: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка базы данных", f"Не удалось инициализировать базу данных: {e}")
            raise

        # Создание интерфейса
        self.setup_ui()
        logger.info("Главное окно приложения создано")



    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        logger.debug("Начало настройки UI")

        # Создание центрального виджета
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Создание основного макета
        main_layout = QVBoxLayout(central_widget)

        # Создание вкладок
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(False)

        # Создание интерфейса — pricing_tab теперь создаётся сразу
        try:
            self.interface = MainInterface(self.db_manager)

            # Установим порядок вкладок: Каталог, Цена изделия, Ввод данных
            self.tab_widget.addTab(self.interface.catalog_tab, "Каталог")  # index 0
            self.tab_widget.addTab(self.interface.pricing_tab, "Цена изделия")  # index 1
            self.tab_widget.addTab(self.interface.input_tab, "Ввод данных")  # index 2

            logger.debug("Интерфейс и вкладки созданы")

            # Подключаем сигналы — pricing_tab теперь точно существует
            self.interface.product_selected_for_editing.connect(self.switch_to_input_tab)
            self.interface.product_selected_for_pricing.connect(self.switch_to_pricing_tab)
            self.interface.pricing_tab.pricing_applied.connect(self.save_pricing_changes)
            logger.debug("Сигнал pricing_applied подключен")

        except Exception as e:
            logger.critical(f"Критическая ошибка при создании интерфейса: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка интерфейса", f"Не удалось создать интерфейс: {e}")
            raise

        # Исправление данных цены
        self.fix_pricing_data()
        self.fix_incorrect_approved_prices()

        main_layout.addWidget(self.tab_widget)

        # По умолчанию открываем "Каталог" (индекс 0)
        self.tab_widget.setCurrentIndex(0)

        # Создание статусной строки
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")
        logger.debug("Статусная строка настроена")

        # Создание меню
        self.create_menu()
        logger.debug("Меню создано")
        logger.info("UI настроен успешно")

    def switch_to_pricing_tab(self, product_id):
        """Переключение на вкладку 'Цена изделия'"""
        logger.debug(f"Переключение на вкладку 'Цена изделия' для изделия ID {product_id}")
        self.tab_widget.setCurrentIndex(1)  # Вкладка "Цена изделия" — индекс 1
        self.interface.pricing_tab.set_product(product_id)

    def switch_to_input_tab(self, product_id):
        """Переключение на вкладку 'Ввод данных'"""
        logger.debug(f"Переключение на вкладку 'Ввод данных' для изделия ID {product_id}")
        self.tab_widget.setCurrentIndex(2)  # Вкладка "Ввод данных" — индекс 2
        self.interface.load_product_to_form(product_id)

    def create_menu(self):
        """Создание меню приложения"""
        logger.debug("Создание меню")
        menubar = self.menuBar()

        # Меню Файл
        file_menu = menubar.addMenu('Файл')

        save_action = file_menu.addAction('Сохранить')
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_product)

        # ДОБАВИМ ЭКСПОРТ СОТРУДНИКОВ
        export_employees_action = file_menu.addAction('Экспорт сотрудников в Excel')
        export_employees_action.triggered.connect(self.export_employees_to_excel)

        load_action = file_menu.addAction('Загрузить')
        load_action.setShortcut('Ctrl+O')
        load_action.triggered.connect(self.load_product)

        file_menu.addSeparator()
        exit_action = file_menu.addAction('Выход')
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)

        # Меню Справочники
        reference_menu = menubar.addMenu('Справочники')

        import_materials_action = reference_menu.addAction('Импорт материалов')
        import_materials_action.triggered.connect(self.import_materials)

        import_rates_action = reference_menu.addAction('Импорт ставок')
        import_rates_action.triggered.connect(self.import_rates)

        # ДОБАВИМ УПРАВЛЕНИЕ СОТРУДНИКАМИ
        manage_employees_action = reference_menu.addAction('Список сотрудников')
        manage_employees_action.triggered.connect(self.manage_employees)

        # Меню Отчеты
        report_menu = menubar.addMenu('Отчеты')

        export_excel_action = report_menu.addAction('Экспорт в Excel')
        export_excel_action.triggered.connect(self.export_to_excel)

        export_pdf_action = report_menu.addAction('Экспорт в PDF')
        export_pdf_action.triggered.connect(self.export_to_pdf)

        # Меню Цена
        price_menu = menubar.addMenu('Цена')

        calculate_price_action = price_menu.addAction('Рассчитать цену изделия')
        calculate_price_action.setShortcut('Ctrl+Shift+C')
        calculate_price_action.triggered.connect(self.calculate_selected_product_price)

    def manage_employees(self):
        """Открытие диалога управления сотрудниками"""
        try:
            from modules.employees_dialog import EmployeesDialog
            dialog = EmployeesDialog(self.db_manager, self)
            dialog.exec_()

            # Обновляем комбобоксы в интерфейсе после закрытия диалога
            if hasattr(self, 'interface'):
                self.interface.load_employees_to_combo()
                if hasattr(self.interface, '_refresh_employee_combos_in_table'):
                    self.interface._refresh_employee_combos_in_table()

        except Exception as e:
            logger.error(f"Ошибка при открытии диалога сотрудников: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при открытии диалога сотрудников: {e}")

    def save_product(self):
        """Сохранение изделия"""
        logger.info("Начало сохранения изделия")
        try:
            # Получение данных из интерфейса
            product_data = {
                'product_id': self.interface.product_id_input.text(),
                'article': self.interface.article_input.text(),
                'name': self.interface.name_input.text()
            }
            logger.debug(f"Данные изделия для сохранения: {product_data}")

            # Определяем, новое это изделие или редактирование существующего
            if self.interface.current_product_id:
                # Обновление существующего изделия
                product_id = self.interface.current_product_id
                self._update_product_in_db(product_id, product_data)
                logger.debug(f"Изделие обновлено в БД с ID: {product_id}")
            else:
                # Создание нового изделия с автоматическим ID
                product_id = self._create_new_product_with_auto_id(product_data)
                logger.debug(f"Новое изделие создано в БД с ID: {product_id}")

            # Сохранение операций и материалов
            self._save_operations_to_db(product_id)
            self._save_materials_to_db(product_id)

            # Сохранение в Excel файл
            file_path = f"data/products/{product_data['article']}_{product_data['name']}.xlsx"
            logger.debug(f"Попытка сохранения в файл: {file_path}")
            success = self.interface.product_manager.save_product_to_excel(product_id, file_path)

            if success:
                logger.info("Изделие успешно сохранено")
                QMessageBox.information(self, "Успех", "Изделие успешно сохранено")
                self.interface.catalog_tab.refresh_catalog()

                # Если это было новое изделие, устанавливаем его как текущее
                if not self.interface.current_product_id:
                    self.interface.current_product_id = product_id
                    # Обновляем отображаемый ID
                    self.interface.product_id_input.setText(str(product_id))
            else:
                logger.error("Ошибка при сохранении изделия")
                QMessageBox.critical(self, "Ошибка", "Ошибка при сохранении изделия")
        except Exception as e:
            logger.error(f"Необработанная ошибка при сохранении изделия: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Необработанная ошибка: {e}")

    def _create_new_product_with_auto_id(self, product_data):
        """Создание нового изделия с автоматическим ID"""
        logger.debug("Создание нового изделия с автоматическим ID")

        # Генерация автоматического ID
        last_id_result = self.db_manager.fetch_one("SELECT MAX(CAST(product_id AS INTEGER)) FROM products")
        last_id = last_id_result[0] if last_id_result and last_id_result[0] else 0
        new_id = str(last_id + 1).zfill(3)

        query = """
            INSERT INTO products (product_id, article, name)
            VALUES (?, ?, ?)
        """
        params = (
            new_id,
            product_data.get('article', ''),
            product_data.get('name', '')
        )

        self.db_manager.execute_query(query, params)

        # Получаем ID созданной записи
        result = self.db_manager.fetch_one("SELECT id FROM products WHERE product_id = ?", (new_id,))
        return result[0] if result else None

    def _update_product_in_db(self, product_id, product_data):
        """Обновление существующего изделия в БД"""
        logger.debug(f"Обновление изделия ID {product_id}")

        query = """
            UPDATE products 
            SET product_id = ?, article = ?, name = ?
            WHERE id = ?
        """
        params = (
            product_data.get('product_id', ''),
            product_data.get('article', ''),
            product_data.get('name', ''),
            product_id
        )

        self.db_manager.execute_query(query, params)
        return product_id

    def _save_operations_to_db(self, product_id):
        """Сохранение операций в БД"""
        logger.debug(f"Сохранение операций для изделия ID {product_id}")
        try:
            operations_data = self.interface.operations_data
            logger.debug(f"Количество операций для сохранения: {len(operations_data)}")

            # Очистка старых операций для этого изделия
            delete_query = "DELETE FROM operations WHERE product_id = ?"
            self.db_manager.execute_query(delete_query, (product_id,))

            for op_data in operations_data:
                query = """
                    INSERT INTO operations 
                    (product_id, operation_name, quantity_measured, time_measured, 
                     time_per_unit, rate_per_minute, cost, employee_id, approved_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    product_id,
                    op_data.get('operation_name', ''),
                    op_data.get('quantity_measured', 0),
                    op_data.get('time_measured', 0.0),
                    op_data.get('time_per_unit', 0.0),
                    op_data.get('rate_per_minute', 0.0),
                    op_data.get('cost', 0.0),
                    op_data.get('employee_id'),
                    op_data.get('approved_rate')
                )
                self.db_manager.execute_query(query, params)
                logger.debug(f"Сохранена операция: {op_data.get('operation_name')}")

            logger.info(f"Сохранено {len(operations_data)} операций для изделия ID {product_id}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении операций: {e}", exc_info=True)
            raise

    def _save_materials_to_db(self, product_id):
        """Сохранение материалов в БД"""
        logger.debug(f"Сохранение материалов для изделия ID {product_id}")
        try:
            materials_data = self.interface.materials_data
            logger.debug(f"Количество материалов для сохранения: {len(materials_data)}")

            # Очистка старых материалов для этого изделия
            delete_query = "DELETE FROM product_materials WHERE product_id = ?"
            self.db_manager.execute_query(delete_query, (product_id,))

            for mat_data in materials_data:
                query = """
                    INSERT INTO product_materials 
                    (product_id, material_id, length, width, thickness, quantity, cost)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    product_id,
                    mat_data.get('material_id'),
                    mat_data.get('length', 0.0),
                    mat_data.get('width', 0.0),
                    mat_data.get('thickness', 0.0),
                    mat_data.get('quantity', 0),
                    mat_data.get('cost', 0.0)
                )
                self.db_manager.execute_query(query, params)
                logger.debug(f"Сохранен материал: {mat_data.get('material_name')}")

            logger.info(f"Сохранено {len(materials_data)} материалов для изделия ID {product_id}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении материалов: {e}", exc_info=True)
            raise

    def save_pricing_changes(self, product_id, pricing_data):
        """Сохранение изменений цены в БД и Excel"""
        logger.info(f"Сохранение изменений цены для изделия ID {product_id}")
        try:
            # Сохраняем данные цены в БД
            self._save_pricing_to_db(product_id, pricing_data)

            # Обновляем Excel файл
            self._update_excel_file(product_id, pricing_data)

            logger.info(f"Изменения цены для изделия ID {product_id} успешно сохранены")

        except Exception as e:
            logger.error(f"Ошибка при сохранении изменений цены: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении изменений цены: {e}")

    def _save_pricing_to_db(self, product_id, pricing_data):
        """Сохранение данных цены в БД"""
        logger.debug(f"Сохранение данных цены в БД для изделия ID {product_id}")

        query = """
            UPDATE products 
            SET overhead_percent = ?, profit_percent = ?, approved_price = ?, calculated_price = ?
            WHERE id = ?
        """

        overhead_percent = float(pricing_data.get('overhead_percent', 0.55))
        profit_percent = float(pricing_data.get('profit_percent', 0.30))
        approved_price = float(pricing_data.get('approved_price', 0.0))
        calculated_price = float(pricing_data.get('calculated_price', 0.0))  # ← новое поле

        logger.debug(
            f"[СОХРАНЕНИЕ_ЦЕНЫ] Сохраняем: overhead={overhead_percent}, profit={profit_percent}, "
            f"approved={approved_price}, calculated={calculated_price}"
        )

        params = (
            overhead_percent,
            profit_percent,
            approved_price,
            calculated_price,  # ← добавлено
            product_id
        )

        self.db_manager.execute_query(query, params)
        logger.debug(f"Параметры цены сохранены в БД для изделия ID {product_id}")

    def _update_excel_file(self, product_id, pricing_data):
        """Обновление Excel файла с новыми данными цены"""
        logger.debug(f"Обновление Excel файла для изделия ID {product_id}")

        # Получаем информацию об изделии для формирования пути к файлу
        product_info = self.db_manager.fetch_one(
            "SELECT article, name FROM products WHERE id = ?",
            (product_id,)
        )

        if product_info:
            article, name = product_info
            file_path = f"data/products/{article}_{name}.xlsx"

            # Обновляем файл через product_manager
            success = self.interface.product_manager.save_product_to_excel(product_id, file_path)

            if success:
                logger.debug(f"Excel файл обновлен: {file_path}")
            else:
                logger.warning(f"Не удалось обновить Excel файл: {file_path}")

    def load_product(self):
        """Загрузка изделия из файла"""
        logger.info("Начало загрузки изделия")
        try:
            QMessageBox.information(self, "Информация", "Функция загрузки изделия будет реализована позже")
            logger.info("Функция загрузки изделия вызвана (временно)")
        except Exception as e:
            logger.error(f"Ошибка при загрузке изделия: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке изделия: {e}")

    def import_materials(self):
        """Импорт материалов из Excel файла"""
        logger.info("Начало импорта материалов")
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Импорт материалов",
                "",
                "Excel Files (*.xlsx)"
            )

            if file_path:
                success = self.interface.material_manager.load_materials_from_excel(file_path)
                if success:
                    QMessageBox.information(self, "Успех", "Материалы успешно импортированы")
                    self.interface.load_categories_to_combo()
                    logger.info("Материалы успешно импортированы")
                else:
                    QMessageBox.critical(self, "Ошибка", "Ошибка при импорте материалов")
                    logger.error("Ошибка при импорте материалов")
        except Exception as e:
            logger.error(f"Ошибка при импорте материалов: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при импорте материалов: {e}")

    def import_rates(self):
        """Импорт ставок из Excel файла"""
        logger.info("Начало импорта ставок")
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Импорт ставок",
                "",
                "Excel Files (*.xlsx)"
            )

            if file_path:
                success = self.interface.rate_manager.load_rates_from_excel(file_path)
                if success:
                    QMessageBox.information(self, "Успех", "Ставки успешно импортированы")
                    self.interface.load_operations_to_combo()
                    logger.info("Ставки успешно импортированы")
                else:
                    QMessageBox.critical(self, "Ошибка", "Ошибка при импорте ставок")
                    logger.error("Ошибка при импорте ставок")
        except Exception as e:
            logger.error(f"Ошибка при импорте ставок: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при импорте ставок: {e}")

    def export_to_excel(self):
        """Экспорт в Excel"""
        logger.info("Начало экспорта в Excel")
        try:
            # Используем каталог для выбора изделия
            if hasattr(self.interface.catalog_tab, 'table_view'):
                current_index = self.interface.catalog_tab.table_view.currentIndex()
                if not current_index.isValid():
                    QMessageBox.warning(self, "Ошибка", "Выберите изделие для экспорта")
                    return

                # Получаем ID изделия из каталога
                row = current_index.row()
                article = self.interface.catalog_tab.model._data[row][1]
                name = self.interface.catalog_tab.model._data[row][2]

                product_info = self.db_manager.fetch_one(
                    "SELECT id FROM products WHERE article = ? AND name = ?",
                    (article, name)
                )

                if product_info:
                    product_id = product_info[0]
                    file_path, _ = QFileDialog.getSaveFileName(
                        self,
                        "Экспорт в Excel",
                        f"data/products/{article}_{name}.xlsx",
                        "Excel Files (*.xlsx)"
                    )

                    if file_path:
                        success = self.interface.report_manager.export_product_to_excel(product_id, file_path)
                        if success:
                            QMessageBox.information(self, "Успех", "Файл успешно экспортирован")
                            logger.info("Файл успешно экспортирован в Excel")
                        else:
                            QMessageBox.critical(self, "Ошибка", "Ошибка при экспорте")
                            logger.error("Ошибка при экспорте в Excel")
            else:
                QMessageBox.warning(self, "Ошибка", "Выберите изделие для экспорта")

        except Exception as e:
            logger.error(f"Ошибка при экспорте в Excel: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при экспорте в Excel: {e}")

    def export_to_pdf(self):
        """Экспорт в PDF"""
        logger.info("Начало экспорта в PDF")
        try:
            QMessageBox.information(self, "Информация", "Функция экспорта в PDF будет реализована позже")
            logger.info("Функция экспорта в PDF вызвана (временно)")
        except Exception as e:
            logger.error(f"Ошибка при экспорте в PDF: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при экспорте в PDF: {e}")

    def calculate_selected_product_price(self):
        """Рассчитать цену для выбранного в каталоге изделия"""
        logger.info("Начало расчета цены для выбранного изделия")
        try:
            if hasattr(self.interface.catalog_tab, 'table_view'):
                current_index = self.interface.catalog_tab.table_view.currentIndex()
                if not current_index.isValid():
                    QMessageBox.warning(self, "Ошибка", "Выберите изделие из каталога для расчета цены.")
                    return

                # Получаем ID изделия из каталога
                row = current_index.row()
                article = self.interface.catalog_tab.model._data[row][1]
                name = self.interface.catalog_tab.model._data[row][2]

                product_info = self.db_manager.fetch_one(
                    "SELECT id FROM products WHERE article = ? AND name = ?",
                    (article, name)
                )

                if product_info:
                    product_id = product_info[0]
                    self.switch_to_pricing_tab(product_id)
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось найти изделие в БД")
            else:
                QMessageBox.warning(self, "Ошибка", "Выберите изделие из каталога для расчета цены.")

        except Exception as e:
            logger.error(f"Ошибка при расчете цены выбранного изделия: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при расчете цены: {e}")

    def fix_pricing_data(self):
        """Исправление некорректных данных цены в БД"""
        logger.info("Исправление некорректных данных цены в БД")
        try:
            products = self.db_manager.fetch_all("""
                SELECT id, overhead_percent, profit_percent, approved_price 
                FROM products 
                WHERE overhead_percent IS NOT NULL AND typeof(overhead_percent) != 'real'
                   OR profit_percent IS NOT NULL AND typeof(profit_percent) != 'real'
                   OR approved_price IS NOT NULL AND typeof(approved_price) != 'real'
            """)

            for product in products:
                product_id, overhead, profit, approved = product
                logger.warning(f"Исправление данных для изделия ID {product_id}")

                # Сбрасываем некорректные значения к значениям по умолчанию
                query = """
                    UPDATE products 
                    SET overhead_percent = 0.55, profit_percent = 0.30, approved_price = 0.0
                    WHERE id = ?
                """
                self.db_manager.execute_query(query, (product_id,))

            logger.info(f"Исправлено {len(products)} изделий с некорректными данными цены")

        except Exception as e:
            logger.error(f"Ошибка при исправлении данных цены: {e}", exc_info=True)

    def fix_incorrect_approved_prices(self):
        """Исправление некорректных утвержденных цен в БД"""
        logger.info("Исправление некорректных утвержденных цен в БД")
        try:
            # Находим изделия с некорректными утвержденными ценами
            products = self.db_manager.fetch_all("""
                SELECT p.id, p.approved_price, 
                       (SELECT SUM(pm.cost) FROM product_materials pm WHERE pm.product_id = p.id) as materials_cost,
                       (SELECT SUM(o.cost) FROM operations o WHERE o.product_id = p.id) as operations_cost
                FROM products p
                WHERE p.approved_price IS NOT NULL 
                  AND (p.approved_price <= 1.0 OR p.approved_price IS NULL)
            """)

            fixed_count = 0
            for product in products:
                product_id, approved_price, materials_cost, operations_cost = product
                materials_cost = materials_cost or 0
                operations_cost = operations_cost or 0

                # Расчет правильной цены
                prime_cost = materials_cost + operations_cost
                overhead_cost = prime_cost * 0.55
                profit_base = prime_cost + overhead_cost
                profit_cost = profit_base * 0.30
                calculated_price = prime_cost + overhead_cost + profit_cost

                if calculated_price > 0:
                    # Обновляем некорректную цену
                    query = "UPDATE products SET approved_price = ? WHERE id = ?"
                    self.db_manager.execute_query(query, (calculated_price, product_id))
                    fixed_count += 1
                    logger.info(
                        f"Исправлена утвержденная цена для изделия ID {product_id}: {approved_price} -> {calculated_price}")

            logger.info(f"Исправлено {fixed_count} изделий с некорректными утвержденными ценами")

        except Exception as e:
            logger.error(f"Ошибка при исправлении утвержденных цен: {e}", exc_info=True)

    def export_employees_to_excel(self):
        """Экспорт сотрудников в Excel файл"""
        logger.info("Экспорт сотрудников в Excel")
        try:
            # Получаем сотрудников из БД
            employees = self.db_manager.fetch_all("SELECT name FROM employees ORDER BY name")

            if not employees:
                QMessageBox.warning(self, "Ошибка", "Нет сотрудников для экспорта")
                return

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Экспорт сотрудников в Excel",
                "data/employees.xlsx",
                "Excel Files (*.xlsx)"
            )

            if file_path:
                import pandas as pd

                # Создаем DataFrame
                df = pd.DataFrame([emp[0] for emp in employees], columns=['ФИО'])

                # Сохраняем в Excel
                df.to_excel(file_path, sheet_name='Сотрудники', index=False)

                QMessageBox.information(self, "Успех", f"Сотрудники экспортированы в {file_path}")
                logger.info(f"Экспортировано {len(employees)} сотрудников в Excel")

        except Exception as e:
            logger.error(f"Ошибка при экспорте сотрудников: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при экспорте сотрудников: {e}")


def main():
    logger.info("ЗАПУСК ГЛАВНОЙ ФУНКЦИИ")
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        logger.debug("QApplication инициализировано")

        # Создаём менеджер базы данных
        db_manager = DatabaseManager()

        # ✅ Добавляем колонку, если её нет
        ensure_calculated_price_column(db_manager)

        # Теперь создаём главное окно
        window = MainApplication()
        # Передаём db_manager вручную, если он создаётся внутри MainApplication — пропустите эту строку
        # ИЛИ: убедитесь, что внутри MainApplication.__init__ тоже вызывается ensure_calculated_price_column

        window.show()
        logger.info("Главное окно показано")

        exit_code = app.exec_()
        logger.info(f"Приложение завершено с кодом выхода: {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске приложения: {e}", exc_info=True)
        QMessageBox.critical(None, "Критическая ошибка", f"Критическая ошибка при запуске приложения: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()