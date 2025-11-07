# modules/materials_dialog.py
import logging
import pandas as pd
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QLineEdit, QFileDialog, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator

logger = logging.getLogger(__name__)


class MaterialsDialog(QDialog):
    # Сигнал для обновления справочника в других модулях (если понадобится)
    materials_updated = pyqtSignal()

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Справочник материалов")
        self.resize(1200, 700)
        self.setup_ui()
        self.load_materials()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # === Панель поиска ===
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Введите текст для поиска по наименованию или категории...")
        self.search_edit.textChanged.connect(self.apply_filter)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # === Таблица материалов ===
        self.table = QTableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            "ID", "Категория", "Наименование", "Диаметр",
            "Сечение (длина)", "Сечение (ширина)", "Толщина",
            "Вес 1 м, кг", "Закупка за т", "Доставка за т", "Брак за т",
            "Закупка за кг", "Ед. изм.", "Наша цена/кг"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        header.sectionClicked.connect(self.sort_by_column)  # Сортировка по клику
        self.table.setSortingEnabled(False)  # Управляем сортировкой вручную из-за фильтрации

        # Разрешаем редактирование всех ячеек (кроме ID)
        self.table.setEditTriggers(QTableWidget.DoubleClicked)
        self.table.itemChanged.connect(self.on_item_changed)

        layout.addWidget(self.table)

        # === Кнопки ===
        button_layout = QHBoxLayout()
        self.export_btn = QPushButton("Экспорт в Excel")
        self.export_btn.clicked.connect(self.export_to_excel)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        self.all_materials = []  # все материалы (без фильтрации)
        self.filtered_materials = []  # отфильтрованные

    def load_materials(self):
        """Загружает все материалы из БД"""
        try:
            query = "SELECT * FROM materials ORDER BY category, name"
            self.all_materials = self.db_manager.fetch_all(query)
            self.apply_filter()  # применяет текущий поиск (если есть)
            logger.info(f"Загружено {len(self.all_materials)} материалов")
        except Exception as e:
            logger.error(f"Ошибка загрузки материалов: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить справочник:\n{e}")

    def apply_filter(self):
        """Применяет фильтр поиска"""
        filter_text = self.search_edit.text().strip().lower()
        if not filter_text:
            self.filtered_materials = self.all_materials
        else:
            self.filtered_materials = [
                row for row in self.all_materials
                if (row[2] and filter_text in row[2].lower()) or  # Наименование
                   (row[1] and filter_text in row[1].lower())      # Категория
            ]
        self.update_table()

    def update_table(self):
        """Обновляет таблицу на основе filtered_materials"""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.filtered_materials))
        for row_idx, row_data in enumerate(self.filtered_materials):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "")
                if col_idx == 0:  # ID — только для чтения
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                else:
                    # Попытка применить числовой валидатор (необязательно, но полезно)
                    if col_idx in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]:
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row_idx, col_idx, item)
        self.table.setSortingEnabled(True)

    def sort_by_column(self, logical_index):
        """Сортировка по клику на заголовок (игнорируем при поиске, чтобы не ломать фильтр)"""
        # В данном случае мы не реализуем сортировку поверх фильтрации,
        # чтобы не усложнять. Можно добавить позже при необходимости.
        pass

    def on_item_changed(self, item):
        """Сохраняет изменение ячейки в БД"""
        try:
            row = item.row()
            col = item.column()
            new_value = item.text().strip()

            # Получаем ID материала из первого столбца
            id_item = self.table.item(row, 0)
            if not id_item:
                return
            material_id = int(id_item.text())

            # Получаем имя колонки для SQL (по порядку)
            column_names = [
                "id", "category", "name", "diameter",
                "section_length", "section_width", "thickness",
                "weight_per_meter", "purchase_price_t", "delivery_price_t",
                "waste_price", "final_price_kg", "unit_of_measurement", "our_price_per_kg"
            ]
            if col >= len(column_names):
                return

            column_name = column_names[col]
            if column_name == "id":
                return  # ID нельзя менять

            # Преобразуем значение в нужный тип (число или строка)
            if column_name in [
                "diameter", "section_length", "section_width", "thickness",
                "weight_per_meter", "supplier_price_per_ton", "delivery_cost_per_ton",
                "waste_cost_per_ton", "supplier_price_per_kg", "our_price", "reserved"
            ]:
                try:
                    float_val = float(new_value.replace(',', '.'))
                    query = f"UPDATE materials SET {column_name} = ? WHERE id = ?"
                    self.db_manager.execute_query(query, (float_val, material_id))
                except ValueError:
                    QMessageBox.warning(self, "Ошибка", f"Неверный формат числа в поле '{column_names[col]}'")
                    # Восстанавливаем старое значение (опционально)
                    return
            else:
                # Строка
                query = f"UPDATE materials SET {column_name} = ? WHERE id = ?"
                self.db_manager.execute_query(query, (new_value, material_id))

            logger.info(f"Обновлён материал ID={material_id}, поле={column_name}, значение={new_value}")
            self.materials_updated.emit()

        except Exception as e:
            logger.error(f"Ошибка при сохранении изменения: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить изменение:\n{e}")

    def export_to_excel(self):
        """Экспортирует текущий (отфильтрованный) список материалов в Excel"""
        try:
            if not self.filtered_materials:
                QMessageBox.warning(self, "Пусто", "Нет данных для экспорта.")
                return

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Экспорт справочника материалов",
                "data/materials_export.xlsx",
                "Excel Files (*.xlsx)"
            )
            if not file_path:
                return

            # Подготавливаем данные
            headers = [
                "ID", "Категория", "Наименование", "Диаметр",
                "Сечение (длина)", "Сечение (ширина)", "Толщина",
                "Вес 1 м, кг", "Закупка розн/т", "Доставка/т", "Брак/т",
                "Закупка за кг", "Наша цена/кг", "Резерв"
            ]
            df = pd.DataFrame(self.filtered_materials, columns=headers)

            # Сохраняем
            df.to_excel(file_path, index=False)
            QMessageBox.information(self, "Успех", f"Справочник экспортирован в:\n{file_path}")
            logger.info(f"Экспорт материалов в {file_path}")

        except Exception as e:
            logger.error(f"Ошибка экспорта в Excel: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать:\n{e}")