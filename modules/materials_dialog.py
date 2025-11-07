# modules/materials_dialog.py
import logging
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QHeaderView
from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)


class MaterialsDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Справочник материалов")
        self.resize(1100, 600)
        self.setup_ui()
        self.load_materials()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            "ID", "Категория", "Наименование", "Диаметр",
            "Сечение (длина)", "Сечение (ширина)", "Толщина",
            "Вес 1 м, кг", "Закупка розн/т", "Доставка/т", "Брак/т",
            "Закупка за кг", "Наша цена/кг", "Резерв"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        layout.addWidget(self.table)

        # Кнопка закрытия
        button_layout = QHBoxLayout()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

    def load_materials(self):
        try:
            # Запрашиваем ВСЕ колонки позиционно — без имён
            query = "SELECT * FROM materials ORDER BY category, name"
            materials = self.db_manager.fetch_all(query)
            self.table.setRowCount(len(materials))
            for row, mat in enumerate(materials):
                for col, value in enumerate(mat):
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(row, col, item)
            logger.info(f"Загружено {len(materials)} материалов в диалог")
        except Exception as e:
            logger.error(f"Ошибка при загрузке справочника: {e}", exc_info=True)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить справочник материалов:\n{e}")