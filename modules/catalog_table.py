# modules/catalog_table.py
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QHeaderView, QPushButton,
    QLineEdit, QLabel, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal
from PyQt5.QtGui import QFont
from modules.database import DatabaseManager
from modules.pricing import PricingManager

logger = logging.getLogger(__name__)


class CatalogTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = [
            "ID", "Артикул", "Наименование\nизделия", "Себестоимость",
            "Материалы", "Работа", "Накладные\nрасходы",
            "Себестоимость+\nнакладные", "Прибыль %", "Прибыль,\nгрн"
        ]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if role == Qt.DisplayRole:
            return self._data[row][col]
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        elif role == Qt.FontRole and col in [3, 4, 5, 6, 7, 9]:  # Числовые колонки
            font = QFont()
            font.setBold(True)
            return font

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        elif orientation == Qt.Horizontal and role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return None

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()


class CatalogTableTab(QWidget):
    # ДОБАВИМ сигналы
    product_selected_for_editing = pyqtSignal(int)
    product_selected_for_pricing = pyqtSignal(int)

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.pricing_manager = PricingManager(db_manager)
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса каталога"""
        logger.debug("[КАТАЛОГ] Инициализация табличного каталога")
        layout = QVBoxLayout(self)

        # Поиск
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по артикулу или названию...")
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(QLabel("Поиск:"))
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Таблица
        self.table_view = QTableView()
        self.model = CatalogTableModel()
        self.table_view.setModel(self.model)

        # Настройка таблицы
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)

        # ИЗМЕНИЛ настройку размеров столбцов
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)  # Разрешаем ручное изменение
        header.setStretchLastSection(True)
        self.table_view.verticalHeader().setVisible(False)

        # Устанавливаем высоту заголовков для двустрочного текста
        header.setFixedHeight(60)

        # Устанавливаем начальные ширины столбцов
        self.table_view.setColumnWidth(0, 80)  # ID
        self.table_view.setColumnWidth(1, 120)  # Артикул
        self.table_view.setColumnWidth(2, 300)  # Наименование изделия (УВЕЛИЧИЛ)
        self.table_view.setColumnWidth(3, 100)  # Себестоимость
        self.table_view.setColumnWidth(4, 100)  # Материалы
        self.table_view.setColumnWidth(5, 100)  # Работа
        self.table_view.setColumnWidth(6, 100)  # Накладные расходы
        self.table_view.setColumnWidth(7, 120)  # Себестоимость+накладные
        self.table_view.setColumnWidth(8, 80)  # Прибыль %
        self.table_view.setColumnWidth(9, 100)  # Прибыль, грн (УВЕЛИЧИЛ)

        # ДОБАВИМ обработку двойного клика
        self.table_view.doubleClicked.connect(self._on_double_click)

        layout.addWidget(self.table_view)

        # Кнопки
        buttons_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.refresh_catalog)

        self.export_btn = QPushButton("Экспорт в Excel")
        self.export_btn.clicked.connect(self.export_catalog)

        self.edit_btn = QPushButton("Редактирование")
        self.edit_btn.clicked.connect(self._on_edit_clicked)

        buttons_layout.addWidget(self.refresh_btn)
        buttons_layout.addWidget(self.export_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

        # Загрузка данных
        self.refresh_catalog()

    def refresh_catalog(self):
        """Обновление данных каталога"""
        logger.debug("[КАТАЛОГ] Обновление данных каталога")
        try:
            products = self.db_manager.fetch_all("""
                SELECT id, product_id, article, name 
                FROM products 
                ORDER BY article, name
            """)

            catalog_data = []
            for product_id, product_id_val, article, name in products:
                # Получаем расчетные данные для каждого изделия
                pricing_data = self.pricing_manager.calculate_pricing(product_id)

                if pricing_data:
                    cost_indicators = pricing_data['cost_indicators']
                    materials_summary = pricing_data['materials_summary']
                    labor_cost = pricing_data['labor_cost']

                    # Сумма материалов
                    total_material_cost = sum(cat_data['total_cost'] for cat_data in materials_summary.values())

                    # Расчет показателей
                    prime_cost = cost_indicators['prime_cost']  # Себестоимость
                    overhead_cost = prime_cost * cost_indicators['overhead_percent']  # Накладные
                    prime_with_overhead = prime_cost + overhead_cost  # Себестоимость + накладные
                    profit_cost = prime_with_overhead * cost_indicators['profit_percent']  # Прибыль в грн
                    profit_percent = cost_indicators['profit_percent'] * 100  # Прибыль в %

                    catalog_data.append([
                        product_id_val or "",
                        article or "",
                        name or "",
                        f"{prime_cost:.2f}",
                        f"{total_material_cost:.2f}",
                        f"{labor_cost:.2f}",
                        f"{overhead_cost:.2f}",
                        f"{prime_with_overhead:.2f}",
                        f"{profit_percent:.1f}%",
                        f"{profit_cost:.2f}"
                    ])
                else:
                    # Если не удалось рассчитать, показываем нули
                    catalog_data.append([
                        product_id_val or "",
                        article or "",
                        name or "",
                        "0.00", "0.00", "0.00", "0.00", "0.00", "0.0%", "0.00"
                    ])

            self.model.update_data(catalog_data)
            logger.info(f"[КАТАЛОГ] Загружено {len(catalog_data)} изделий")

        except Exception as e:
            logger.error(f"[КАТАЛОГ] Ошибка при обновлении каталога: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке каталога: {e}")

    def _on_search_changed(self, text):
        """Обработка изменения поискового запроса"""
        # TODO: Реализовать фильтрацию
        pass

    def _on_edit_clicked(self):
        """Обработка нажатия кнопки редактирования"""
        try:
            current_index = self.table_view.currentIndex()
            if not current_index.isValid():
                QMessageBox.warning(self, "Ошибка", "Выберите изделие для редактирования")
                return

            # Получаем ID изделия из БД по отображаемым данным
            row = current_index.row()
            article = self.model._data[row][1]  # Артикул во втором столбце
            name = self.model._data[row][2]  # Название в третьем столбце

            # Находим реальный ID изделия в БД
            product_info = self.db_manager.fetch_one(
                "SELECT id FROM products WHERE article = ? AND name = ?",
                (article, name)
            )

            if product_info:
                product_id = product_info[0]
                logger.info(f"[КАТАЛОГ] Редактирование изделия ID {product_id}")

                # Испускаем сигнал для переключения на редактирование
                self.product_selected_for_editing.emit(product_id)
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось найти изделие в БД")
                logger.error(f"[КАТАЛОГ] Изделие не найдено: {article} - {name}")

        except Exception as e:
            logger.error(f"[КАТАЛОГ] Ошибка при редактировании: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при редактировании: {e}")

    def _on_double_click(self, index):
        """Обработка двойного клика по строке"""
        try:
            if not index.isValid():
                return

            # Получаем ID изделия из БД по отображаемым данным
            row = index.row()
            article = self.model._data[row][1]  # Артикул во втором столбце
            name = self.model._data[row][2]  # Название в третьем столбце

            # Находим реальный ID изделия в БД
            product_info = self.db_manager.fetch_one(
                "SELECT id FROM products WHERE article = ? AND name = ?",
                (article, name)
            )

            if product_info:
                product_id = product_info[0]
                logger.info(f"[КАТАЛОГ] Двойной клик по изделию ID {product_id}")

                # Испускаем сигнал для переключения на вкладку цены
                self.product_selected_for_pricing.emit(product_id)
            else:
                logger.error(f"[КАТАЛОГ] Изделие не найдено: {article} - {name}")

        except Exception as e:
            logger.error(f"[КАТАЛОГ] Ошибка при двойном клике: {e}", exc_info=True)

    def export_catalog(self):
        """Экспорт каталога в Excel"""
        logger.info("[КАТАЛОГ] Экспорт каталога в Excel")
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Экспорт каталога в Excel",
                "data/catalog/каталог_изделий.xlsx",
                "Excel Files (*.xlsx)"
            )

            if file_path:
                success = self._export_to_excel(file_path)
                if success:
                    QMessageBox.information(self, "Успех", "Каталог успешно экспортирован в Excel")
                    logger.info("[КАТАЛОГ] Каталог экспортирован в Excel")
                else:
                    QMessageBox.critical(self, "Ошибка", "Ошибка при экспорте каталога")
                    logger.error("[КАТАЛОГ] Ошибка при экспорте каталога")

        except Exception as e:
            logger.error(f"[КАТАЛОГ] Ошибка при экспорте каталога: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при экспорте: {e}")

    def _export_to_excel(self, file_path):
        """Экспорт данных каталога в Excel"""
        try:
            import pandas as pd
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment

            # Создаем DataFrame из данных модели
            headers = [
                'ID', 'Артикул', 'Наименование изделия', 'Себестоимость',
                'Материалы', 'Работа', 'Накладные расходы',
                'Себестоимость+накладные', 'Прибыль %', 'Прибыль, грн'
            ]

            df = pd.DataFrame(self.model._data, columns=headers)

            # Сохраняем в Excel с форматированием
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Каталог изделий', index=False)

                # Получаем лист для форматирования
                worksheet = writer.sheets['Каталог изделий']

                # Форматируем заголовки
                for col in range(1, len(headers) + 1):
                    cell = worksheet.cell(row=1, column=col)
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

                # Автоподбор ширины колонок
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

                # Устанавливаем высоту строки для заголовков
                worksheet.row_dimensions[1].height = 40

            return True

        except Exception as e:
            logger.error(f"[КАТАЛОГ] Ошибка при экспорте в Excel: {e}", exc_info=True)
            return False