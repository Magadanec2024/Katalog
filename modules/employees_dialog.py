# modules/employees_dialog.py
import sys
import os

from pathlib import Path

# Автоматически находим путь к плагинам в текущем виртуальном окружении
venv_base = Path(sys.executable).parent.parent  # поднимаемся из Scripts/
plugins_path = venv_base / "Lib" / "site-packages" / "PyQt5" / "Qt5" / "plugins"

if plugins_path.exists():
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins_path)
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMessageBox, QInputDialog, QLineEdit,
    QLabel, QFormLayout, QDialogButtonBox, QGroupBox, QComboBox
)
from PyQt5.QtCore import Qt
from modules.database import DatabaseManager

logger = logging.getLogger(__name__)


class EmployeesDialog(QDialog):
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Управление сотрудниками")
        self.setGeometry(200, 200, 900, 700)

        self.all_employees = []
        self.init_ui()
        self.load_employees()

    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)

        # Панель поиска и фильтрации
        filter_layout = QHBoxLayout()

        # Поиск
        filter_layout.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Введите фамилию, имя или должность...")
        self.search_edit.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.search_edit)

        # Группировка
        filter_layout.addWidget(QLabel("Группировка:"))
        self.group_combo = QComboBox()
        self.group_combo.addItem("Без группировки", "")
        self.group_combo.addItem("По должности", "position")
        self.group_combo.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.group_combo)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Таблица сотрудников
        self.employees_table = QTableWidget()
        self.employees_table.setColumnCount(4)
        self.employees_table.setHorizontalHeaderLabels(["ID", "Фамилия", "Имя", "Должность"])
        self.employees_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.employees_table.setSortingEnabled(True)
        layout.addWidget(self.employees_table)

        # Кнопки управления
        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.add_employee)

        self.edit_btn = QPushButton("Редактировать")
        self.edit_btn.clicked.connect(self.edit_employee)

        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_employee)

        self.export_btn = QPushButton("Экспорт в Excel")
        self.export_btn.clicked.connect(self.export_to_excel)

        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.delete_btn)
        buttons_layout.addWidget(self.export_btn)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

        # Статистика
        self.stats_label = QLabel("Всего сотрудников: 0")
        layout.addWidget(self.stats_label)

        # Кнопки OK/Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_employees(self):
        """Загрузка всех сотрудников из БД"""
        try:
            self.all_employees = self.db_manager.fetch_all("""
                SELECT id, name, surname, position 
                FROM employees 
                ORDER BY surname, name
            """)

            self.apply_filters()
            logger.debug(f"Загружено {len(self.all_employees)} сотрудников")

        except Exception as e:
            logger.error(f"Ошибка при загрузке сотрудников: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке сотрудников: {e}")

    def apply_filters(self):
        """Применение фильтров и группировки"""
        search_text = self.search_edit.text().strip().lower()
        group_by = self.group_combo.currentData()

        # Фильтрация
        filtered_employees = []
        for emp in self.all_employees:
            emp_id, name, surname, position = emp
            full_name = f"{surname} {name}".strip()

            # Поиск без учета регистра
            if (search_text in full_name.lower() or
                    search_text in name.lower() or
                    search_text in surname.lower() or
                    (position and search_text in position.lower())):
                filtered_employees.append(emp)

        # Группировка
        if group_by == "position":
            self.show_grouped_by_position(filtered_employees)
        else:
            self.show_ungrouped(filtered_employees)

        # Обновление статистики
        self.stats_label.setText(
            f"Всего сотрудников: {len(filtered_employees)} (отфильтровано из {len(self.all_employees)})")

    def show_ungrouped(self, employees):
        """Показать сотрудников без группировки"""
        self.employees_table.setRowCount(len(employees))

        for row, (emp_id, name, surname, position) in enumerate(employees):
            self.employees_table.setItem(row, 0, QTableWidgetItem(str(emp_id)))
            self.employees_table.setItem(row, 1, QTableWidgetItem(surname or ""))
            self.employees_table.setItem(row, 2, QTableWidgetItem(name or ""))
            self.employees_table.setItem(row, 3, QTableWidgetItem(position or ""))

    def show_grouped_by_position(self, employees):
        """Показать сотрудников с группировкой по должностям"""
        # Группируем по должностям
        positions = {}
        for emp in employees:
            emp_id, name, surname, position = emp
            position_key = position if position else "Без должности"
            if position_key not in positions:
                positions[position_key] = []
            positions[position_key].append(emp)

        # Подсчитываем общее количество строк (сотрудники + заголовки групп)
        total_rows = sum(len(emps) + 1 for emps in positions.values())
        self.employees_table.setRowCount(total_rows)

        current_row = 0
        for position, emps in sorted(positions.items()):
            # Заголовок группы
            header_item = QTableWidgetItem(f"--- {position} ({len(emps)} чел.) ---")
            header_item.setBackground(Qt.lightGray)
            header_item.setFlags(Qt.ItemIsEnabled)  # Не редактируемый
            self.employees_table.setItem(current_row, 1, header_item)
            current_row += 1

            # Сотрудники в группе
            for emp_id, name, surname, _ in emps:
                self.employees_table.setItem(current_row, 0, QTableWidgetItem(str(emp_id)))
                self.employees_table.setItem(current_row, 1, QTableWidgetItem(surname or ""))
                self.employees_table.setItem(current_row, 2, QTableWidgetItem(name or ""))
                self.employees_table.setItem(current_row, 3,
                                             QTableWidgetItem(position if position != "Без должности" else ""))
                current_row += 1

    def add_employee(self):
        """Добавление нового сотрудника"""
        dialog = EmployeeEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, surname, position = dialog.get_data()
            if name:
                try:
                    # Проверка на дубликат (без учета регистра)
                    existing = self.db_manager.fetch_one(
                        "SELECT id FROM employees WHERE LOWER(name) = LOWER(?) AND LOWER(surname) = LOWER(?)",
                        (name, surname)
                    )
                    if existing:
                        full_name = f"{surname} {name}".strip()
                        QMessageBox.warning(self, "Ошибка", f"Сотрудник '{full_name}' уже существует")
                        return

                    # Добавление в БД
                    query = "INSERT INTO employees (name, surname, position) VALUES (?, ?, ?)"
                    self.db_manager.execute_query(query, (name, surname, position))

                    # Перезагружаем все данные
                    self.load_employees()
                    QMessageBox.information(self, "Успех", "Сотрудник добавлен")

                except Exception as e:
                    logger.error(f"Ошибка при добавлении сотрудника: {e}")
                    QMessageBox.critical(self, "Ошибка", f"Ошибка при добавлении сотрудника: {e}")

    def edit_employee(self):
        """Редактирование выбранного сотрудника"""
        current_row = self.employees_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите сотрудника для редактирования")
            return

        # Получаем ID сотрудника (может быть в разных строках из-за группировки)
        emp_id_item = self.employees_table.item(current_row, 0)
        if not emp_id_item:
            QMessageBox.warning(self, "Ошибка", "Выберите строку с сотрудником (не заголовок группы)")
            return

        emp_id = int(emp_id_item.text())
        current_surname = self.employees_table.item(current_row, 1).text() or ""
        current_name = self.employees_table.item(current_row, 2).text()
        current_position = self.employees_table.item(current_row, 3).text() or ""

        dialog = EmployeeEditDialog(self, current_name, current_surname, current_position)
        if dialog.exec_() == QDialog.Accepted:
            name, surname, position = dialog.get_data()
            if name:
                try:
                    # Проверка на дубликат (без учета регистра, кроме текущего сотрудника)
                    existing = self.db_manager.fetch_one(
                        "SELECT id FROM employees WHERE LOWER(name) = LOWER(?) AND LOWER(surname) = LOWER(?) AND id != ?",
                        (name, surname, emp_id)
                    )
                    if existing:
                        full_name = f"{surname} {name}".strip()
                        QMessageBox.warning(self, "Ошибка", f"Сотрудник '{full_name}' уже существует")
                        return

                    # Обновление в БД
                    query = "UPDATE employees SET name = ?, surname = ?, position = ? WHERE id = ?"
                    self.db_manager.execute_query(query, (name, surname, position, emp_id))

                    # Перезагружаем все данные
                    self.load_employees()
                    QMessageBox.information(self, "Успех", "Данные сотрудника обновлены")

                except Exception as e:
                    logger.error(f"Ошибка при редактировании сотрудника: {e}")
                    QMessageBox.critical(self, "Ошибка", f"Ошибка при редактировании сотрудника: {e}")

    def delete_employee(self):
        """Удаление выбранного сотрудника"""
        current_row = self.employees_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите сотрудника для удаления")
            return

        # Получаем ID сотрудника
        emp_id_item = self.employees_table.item(current_row, 0)
        if not emp_id_item:
            QMessageBox.warning(self, "Ошибка", "Выберите строку с сотрудником (не заголовок группы)")
            return

        emp_id = int(emp_id_item.text())
        emp_surname = self.employees_table.item(current_row, 1).text() or ""
        emp_name = self.employees_table.item(current_row, 2).text()
        full_name = f"{emp_surname} {emp_name}".strip()

        # Проверка использования сотрудника в операциях
        usage = self.db_manager.fetch_one(
            "SELECT COUNT(*) FROM operations WHERE employee_id = ?",
            (emp_id,)
        )

        if usage and usage[0] > 0:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Сотрудник '{full_name}' используется в {usage[0]} операциях.\n"
                "Сначала удалите или измените эти операции."
            )
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить сотрудника '{full_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.db_manager.execute_query("DELETE FROM employees WHERE id = ?", (emp_id,))
                self.load_employees()
                QMessageBox.information(self, "Успех", "Сотрудник удален")
            except Exception as e:
                logger.error(f"Ошибка при удалении сотрудника: {e}")
                QMessageBox.critical(self, "Ошибка", f"Ошибка при удалении сотрудника: {e}")

    def export_to_excel(self):
        """Экспорт сотрудников в Excel"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            import pandas as pd

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Экспорт сотрудников в Excel",
                "data/employees.xlsx",
                "Excel Files (*.xlsx)"
            )

            if file_path:
                employees = self.db_manager.fetch_all("""
                    SELECT surname, name, position 
                    FROM employees 
                    ORDER BY surname, name
                """)

                df = pd.DataFrame(employees, columns=['Фамилия', 'Имя', 'Должность'])
                df.to_excel(file_path, sheet_name='Сотрудники', index=False)

                QMessageBox.information(self, "Успех", f"Сотрудники экспортированы в {file_path}")

        except Exception as e:
            logger.error(f"Ошибка при экспорте сотрудников: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при экспорте: {e}")


class EmployeeEditDialog(QDialog):
    def __init__(self, parent=None, name="", surname="", position=""):
        super().__init__(parent)
        self.setWindowTitle("Редактирование сотрудника")
        self.setModal(True)
        self.setFixedSize(400, 200)

        self.name_edit = QLineEdit(name)
        self.surname_edit = QLineEdit(surname)
        self.position_edit = QLineEdit(position)

        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        layout.addRow("Фамилия:", self.surname_edit)
        layout.addRow("Имя:*", self.name_edit)
        layout.addRow("Должность:", self.position_edit)

        note_label = QLabel("* - обязательное поле")
        note_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addRow("", note_label)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)

        layout.addRow(button_box)

    def validate_and_accept(self):
        """Валидация и принятие данных"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите имя сотрудника")
            self.name_edit.setFocus()
            return
        self.accept()

    def get_data(self):
        return (self.name_edit.text().strip(),
                self.surname_edit.text().strip(),
                self.position_edit.text().strip())