# modules/catalog_table.py

import sys
import os

from pathlib import Path

# Автоматически находим путь к плагинам в текущем виртуальном окружении
venv_base = Path(sys.executable).parent.parent  # поднимаемся из Scripts/
plugins_path = venv_base / "Lib" / "site-packages" / "PyQt5" / "Qt5" / "plugins"

if plugins_path.exists():
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins_path)
# modules/catalog_table.py
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QLineEdit, QLabel,
    QComboBox, QDialog, QFormLayout, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
import pandas as pd

logger = logging.getLogger(__name__)


class CatalogTable(QWidget):
    """Виджет каталога изделий с расширенным функционалом"""

    # Сигналы для взаимодействия с другими модулями
    product_selected = pyqtSignal(int)  # product_id
    product_deleted = pyqtSignal(int)  # product_id
    catalog_updated = pyqtSignal()  # каталог обновлен
    product_edit_requested = pyqtSignal(int)  # запрос на редактирование

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_products = []

        self.init_ui()
        self.load_products()

    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)

        # Панель поиска и фильтрации
        filter_layout = QHBoxLayout()

        # Поиск
        filter_layout.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по артикулу или названию...")
        self.search_edit.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.search_edit)

        # Сортировка
        filter_layout.addWidget(QLabel("Сортировка:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("По артикулу", "article")
        self.sort_combo.addItem("По названию", "name")
        self.sort_combo.addItem("По дате создания", "created_date")
        self.sort_combo.addItem("По утвержденной цене", "approved_price")
        self.sort_combo.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.sort_combo)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Таблица каталога - УВЕЛИЧИВАЕМ количество столбцов
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(11)
        self.products_table.setHorizontalHeaderLabels([
            "ID", "Артикул", "Название", "Материал", "Работа",
            "Себестоимость", "Накладные", "Прибыль",
            "Расчётная цена", "Утверждённая цена", "Дата создания"
        ])

        # Настройка таблицы
        header = self.products_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Артикул
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Название
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Материал
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Работа
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Себестоимость
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Накладные
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Прибыль
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Расчётная
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Утверждённая
        header.setSectionResizeMode(10, QHeaderView.ResizeToContents)  # Дата

        self.products_table.setSortingEnabled(True)
        self.products_table.doubleClicked.connect(self.on_product_double_click)
        layout.addWidget(self.products_table)

        # Кнопки управления - ДОБАВЛЯЕМ кнопку редактирования
        buttons_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.load_products)

        self.edit_btn = QPushButton("Редактировать")  # НОВАЯ КНОПКА
        self.edit_btn.clicked.connect(self.edit_selected_product)

        self.export_btn = QPushButton("Экспорт в Excel")
        self.export_btn.clicked.connect(self.export_to_excel)

        self.delete_btn = QPushButton("Удалить выбранное")
        self.delete_btn.clicked.connect(self.delete_selected_product)
        self.delete_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; }")

        buttons_layout.addWidget(self.refresh_btn)
        buttons_layout.addWidget(self.edit_btn)  # ДОБАВЛЯЕМ КНОПКУ
        buttons_layout.addWidget(self.export_btn)
        buttons_layout.addWidget(self.delete_btn)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

        # Статистика
        self.stats_label = QLabel("Всего изделий: 0")
        layout.addWidget(self.stats_label)

    def load_products(self):
        """Загрузка изделий из базы данных с ценами и расчетами"""
        try:
            # Получаем изделия с ценами и расчетами
            query = """
                SELECT p.id, p.product_id, p.article, p.name, p.created_date,
                       p.approved_price, p.calculated_price,
                       (SELECT SUM(o.cost) FROM operations o WHERE o.product_id = p.id) as operations_cost,
                       (SELECT SUM(pm.cost) FROM product_materials pm WHERE pm.product_id = p.id) as materials_cost
                FROM products p
                ORDER BY p.created_date DESC
            """

            self.current_products = self.db_manager.fetch_all(query)
            self.apply_filters()

            logger.info(f"Загружено {len(self.current_products)} изделий в каталог")

        except Exception as e:
            logger.error(f"Ошибка при загрузке изделий в каталог: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке каталога: {e}")

    def apply_filters(self):
        """Применение фильтров и сортировки"""
        search_text = self.search_edit.text().strip().lower()
        sort_by = self.sort_combo.currentData()

        # Фильтрация
        filtered_products = []
        for product in self.current_products:
            product_id, prod_id, article, name, created_date, approved_price, calculated_price_db, ops_cost, mat_cost = product

            # Расчет стоимости
            operations_cost = ops_cost if ops_cost else 0
            materials_cost = mat_cost if mat_cost else 0
            prime_cost = operations_cost + materials_cost  # Себестоимость

            # Расчёт накладных и прибыли (как в UI)
            overhead = prime_cost * 0.55
            profit_base = prime_cost + overhead
            profit = profit_base * 0.30
            calculated_price = prime_cost + overhead + profit

            # Используем расчётную цену из БД, если она есть (для согласованности)
            if calculated_price_db is not None:
                calculated_price = calculated_price_db

            # Поиск
            if (search_text in (article or "").lower() or
                    search_text in (name or "").lower() or
                    search_text in (prod_id or "").lower()):
                filtered_products.append((
                    product_id, prod_id, article, name, created_date,
                    approved_price, calculated_price,
                    materials_cost, operations_cost, prime_cost, overhead, profit
                ))

        # Сортировка
        if sort_by == "article":
            filtered_products.sort(key=lambda x: x[2] or "")
        elif sort_by == "name":
            filtered_products.sort(key=lambda x: x[3] or "")
        elif sort_by == "approved_price":
            filtered_products.sort(key=lambda x: x[5] or 0, reverse=True)
        else:  # created_date
            filtered_products.sort(key=lambda x: x[4] or "", reverse=True)

        # Обновление таблицы
        self.update_products_table(filtered_products)

        # Статистика
        self.stats_label.setText(f"Всего изделий: {len(filtered_products)}")

    def update_products_table(self, products):
        """Обновление таблицы изделий с дополнительными полями"""
        self.products_table.setRowCount(len(products))

        for row, (product_id, prod_id, article, name, created_date,
                  approved_price, calculated_price,
                  materials_cost, operations_cost, prime_cost, overhead, profit) in enumerate(products):

            # ID
            self.products_table.setItem(row, 0, QTableWidgetItem(str(product_id)))
            # Артикул
            self.products_table.setItem(row, 1, QTableWidgetItem(article or ""))
            # Название
            self.products_table.setItem(row, 2, QTableWidgetItem(name or ""))
            # Материал
            mat_item = QTableWidgetItem(f"{materials_cost:.2f} грн")
            mat_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.products_table.setItem(row, 3, mat_item)
            # Работа
            op_item = QTableWidgetItem(f"{operations_cost:.2f} грн")
            op_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.products_table.setItem(row, 4, op_item)
            # Себестоимость
            prime_item = QTableWidgetItem(f"{prime_cost:.2f} грн")
            prime_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.products_table.setItem(row, 5, prime_item)
            # Накладные
            overhead_item = QTableWidgetItem(f"{overhead:.2f} грн")
            overhead_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.products_table.setItem(row, 6, overhead_item)
            # Прибыль
            profit_item = QTableWidgetItem(f"{profit:.2f} грн")
            profit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.products_table.setItem(row, 7, profit_item)
            # Расчётная цена
            calc_item = QTableWidgetItem(f"{calculated_price:.2f} грн")
            calc_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.products_table.setItem(row, 8, calc_item)
            # Утверждённая цена
            approved_item = QTableWidgetItem(f"{approved_price:.2f} грн" if approved_price else "Не утверждена")
            approved_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # Визуальное сравнение цен
            if approved_price and calculated_price:
                price_diff = abs(approved_price - calculated_price)
                if price_diff > 0.01:
                    if approved_price > calculated_price:
                        color = QColor(255, 255, 200)  # светло-жёлтый
                    else:
                        color = QColor(255, 200, 200)  # светло-красный
                    calc_item.setBackground(color)
                    approved_item.setBackground(color)
                else:
                    color = QColor(200, 255, 200)  # светло-зелёный
                    calc_item.setBackground(color)
                    approved_item.setBackground(color)

            self.products_table.setItem(row, 9, approved_item)
            # Дата создания
            date_item = QTableWidgetItem(created_date[:10] if created_date else "")
            date_item.setTextAlignment(Qt.AlignCenter)
            self.products_table.setItem(row, 10, date_item)

    def edit_selected_product(self):
        """Редактирование выбранного изделия"""
        current_row = self.products_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите изделие для редактирования")
            return

        # Получаем ID изделия
        product_id_item = self.products_table.item(current_row, 0)
        if not product_id_item:
            QMessageBox.warning(self, "Ошибка", "Не удалось получить ID изделия")
            return

        product_id = int(product_id_item.text())
        logger.info(f"Запрос на редактирование изделия ID {product_id}")

        # Отправляем сигнал для открытия редактора
        self.product_edit_requested.emit(product_id)

    # Остальные методы остаются без изменений
    def on_product_double_click(self, index):
        """Обработка двойного клика по изделию"""
        row = index.row()
        product_id_item = self.products_table.item(row, 0)

        if product_id_item:
            product_id = int(product_id_item.text())
            logger.info(f"Выбрано изделие ID {product_id} в каталоге")
            self.product_selected.emit(product_id)

    def delete_selected_product(self):
        """Удаление выбранного изделия"""
        current_row = self.products_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите изделие для удаления")

        # Уведомляем интерфейс, что изделие удалено
        if hasattr(self.parent(), 'on_catalog_product_deleted'):
            self.parent().on_catalog_product_deleted(product_id)
            return

        # Получаем ID изделия
        product_id_item = self.products_table.item(current_row, 0)
        if not product_id_item:
            QMessageBox.warning(self, "Ошибка", "Не удалось получить ID изделия")
            return

        product_id = int(product_id_item.text())
        product_name = self.products_table.item(current_row, 2).text() or "Неизвестно"

        # Подтверждение удаления
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить изделие '{product_name}'?\n\n"
            "Это действие удалит все связанные операции и материалы!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Удаляем через db_manager
                self.db_manager.execute_query("DELETE FROM operations WHERE product_id = ?", (product_id,))
                self.db_manager.execute_query("DELETE FROM product_materials WHERE product_id = ?", (product_id,))
                self.db_manager.execute_query("DELETE FROM products WHERE id = ?", (product_id,))

                # Обновляем каталог
                self.load_products()

                # Отправляем сигнал
                self.product_deleted.emit(product_id)
                self.catalog_updated.emit()

                QMessageBox.information(self, "Успех", "Изделие удалено")
                logger.info(f"Изделие ID {product_id} удалено из каталога")

            except Exception as e:
                logger.error(f"Ошибка при удалении изделия: {e}", exc_info=True)
                QMessageBox.critical(self, "Ошибка", f"Ошибка при удалении изделия: {e}")

    def export_to_excel(self):
        """Экспорт каталога в Excel"""
        try:
            from PyQt5.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Экспорт каталога в Excel",
                "data/catalog_export.xlsx",
                "Excel Files (*.xlsx)"
            )

            if file_path:
                # Подготавливаем данные для экспорта
                export_data = []
                for row in range(self.products_table.rowCount()):
                    row_data = []
                    for col in range(self.products_table.columnCount()):
                        item = self.products_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    export_data.append(row_data)

                # Создаем DataFrame
                df = pd.DataFrame(export_data, columns=[
                    "ID", "Артикул", "Название", "Себестоимость", "Накладные", "Прибыль",
                    "Расчетная цена", "Утвержденная цена", "Дата создания"
                ])

                # Экспортируем
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "Успех", f"Каталог экспортирован в {file_path}")
                logger.info(f"Каталог экспортирован в {file_path}")

        except Exception as e:
            logger.error(f"Ошибка при экспорте каталога: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при экспорте: {e}")

    def refresh_catalog(self):
        """Публичный метод для обновления каталога извне"""
        self.load_products()