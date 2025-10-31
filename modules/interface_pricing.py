# modules/interface_pricing.py
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QDoubleSpinBox, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QMessageBox, QHeaderView, QApplication,
    QSizePolicy, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from modules.pricing import PricingManager
from modules.database import DatabaseManager

logger = logging.getLogger(__name__)


class PricingTab(QWidget):
    # Сигнал, который будет испускаться при успешном обновлении цены
    pricing_updated = pyqtSignal(int, object)  # product_id, pricing_data
    pricing_applied = pyqtSignal(int, object)  # product_id, pricing_data

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.pricing_manager = PricingManager(db_manager)
        self.current_product_id = None

        # Переменные для хранения текущих расчетных значений
        self._current_prime_cost = 0.0
        self._current_overhead_percent = 0.55  # 55% по умолчанию
        self._current_profit_percent = 0.30  # 30% по умолчанию
        self._current_calculated_price = 0.0
        self._current_approved_price = 0.0

        # Флаг для предотвращения рекурсивных обновлений
        self._updating = False

        self._init_ui()

    def _init_ui(self):
        """Инициализация интерфейса вкладки"""
        logger.debug("[ЦЕНА_ИНТЕРФЕЙС] === ИНИЦИАЛИЗАЦИЯ UI ВКЛАДКИ 'ЦЕНА ИЗДЕЛИЯ' ===")
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # Создаем все группы
        self.info_group = self._create_info_group()
        main_layout.addWidget(self.info_group)

        self.materials_summary_group = self._create_materials_summary_group()
        main_layout.addWidget(self.materials_summary_group)

        self.labor_cost_group = self._create_labor_cost_group()
        main_layout.addWidget(self.labor_cost_group)

        self.cost_indicators_group = self._create_cost_indicators_group()
        main_layout.addWidget(self.cost_indicators_group)

        # Кнопки управления
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.update_button = QPushButton("Обновить")
        self.update_button.clicked.connect(self._on_update_clicked)
        self.update_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        buttons_layout.addWidget(self.update_button)

        self.reset_approved_price_btn = QPushButton("Сбросить на расчетную")
        self.reset_approved_price_btn.clicked.connect(self._on_reset_approved_price)
        self.reset_approved_price_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        buttons_layout.addWidget(self.reset_approved_price_btn)

        self.apply_button = QPushButton("Применить")
        self.apply_button.clicked.connect(self._on_apply_clicked)
        self.apply_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.apply_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        buttons_layout.addWidget(self.apply_button)

        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)

        # Изначально блокируем поля ввода
        self._set_fields_enabled(False)

        # Минимальная высота для таблицы материалов
        self.materials_table.setMinimumHeight(150)
        logger.debug("[ЦЕНА_ИНТЕРФЕЙС] === ИНИЦИАЛИЗАЦИЯ UI ЗАВЕРШЕНА ===")

    def _on_apply_clicked(self):
        """Обработчик нажатия кнопки 'Применить'"""
        logger.info("[ЦЕНА_ИНТЕРФЕЙС] Нажата кнопка 'Применить'")
        try:
            if not self.current_product_id:
                QMessageBox.warning(self, "Ошибка", "Нет выбранного изделия для применения изменений")
                return

            # Собираем данные
            approved_price = self.approved_price_spinbox.value()
            pricing_data = self._collect_current_pricing_data()

            # Сохраняем утвержденную цену в базе
            query = "UPDATE products SET approved_price = ? WHERE id = ?"
            self.db_manager.execute_query(query, (approved_price, self.current_product_id))
            logger.info(
                f"[ЦЕНА_ИНТЕРФЕЙС] Утвержденная цена {approved_price:.2f} грн сохранена в БД для изделия ID {self.current_product_id}")

            # Обновляем внутренние значения
            self._current_approved_price = approved_price
            self._update_price_display(self._current_calculated_price, approved_price)

            # Испускаем сигнал
            self.pricing_applied.emit(self.current_product_id, pricing_data)
            QMessageBox.information(self, "Успех", "Утвержденная цена успешно сохранена.")

        except Exception as e:
            logger.error(f"[ЦЕНА_ИНТЕРФЕЙС] Ошибка при применении изменений: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении утвержденной цены: {e}")

    def _collect_current_pricing_data(self):
        """Сбор текущих данных расчета цены"""
        logger.debug("[ЦЕНА_ИНТЕРФЕЙС] Сбор текущих данных расчета цены")

        pricing_data = {
            'overhead_percent': self.overhead_percent_spinbox.value() / 100.0,
            'profit_percent': self.profit_percent_spinbox.value() / 100.0,
            'approved_price': self.approved_price_spinbox.value(),
            'calculated_price': self._current_calculated_price,
            'prime_cost': self._current_prime_cost
        }

        logger.debug(f"[ЦЕНА_ИНТЕРФЕЙС] Собранные данные: {pricing_data}")
        return pricing_data

    def _create_info_group(self):
        """Создание группы с основной информацией об изделии"""
        logger.debug("[ЦЕНА_ИНТЕРФЕЙС] Создание группы 'Общая информация'")
        group = QGroupBox("1. Общая информация")
        layout = QFormLayout(group)
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.article_label = QLabel("-")
        self.article_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.name_label = QLabel("-")
        self.name_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.total_weight_label = QLabel("0.000 кг")
        self.total_paint_area_label = QLabel("0.000 м²")

        self.total_weight_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.total_paint_area_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addRow("Артикул:", self.article_label)
        layout.addRow("Наименование:", self.name_label)
        layout.addRow("Вес изделия:", self.total_weight_label)
        layout.addRow("Площадь покраски:", self.total_paint_area_label)

        return group

    def _create_materials_summary_group(self):
        """Создание группы описания категорий материалов"""
        logger.debug("[ЦЕНА_ИНТЕРФЕЙС] Создание группы 'Описание категорий материалов'")
        group = QGroupBox("2. Описание категорий материалов")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(5, 5, 5, 5)

        self.materials_table = QTableWidget()
        self.materials_table.setColumnCount(3)
        self.materials_table.setHorizontalHeaderLabels(
            ["Категория материалов", "Суммарный вес (кг)", "Суммарная стоимость (грн)"])
        self.materials_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.materials_table.verticalHeader().setVisible(False)
        self.materials_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout.addWidget(self.materials_table)

        return group

    def _create_labor_cost_group(self):
        """Создание группы стоимости работ"""
        logger.debug("[ЦЕНА_ИНТЕРФЕЙС] Создание группы 'Стоимость всех работ'")
        group = QGroupBox("3. Стоимость всех работ")
        layout = QFormLayout(group)
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.labor_cost_label = QLabel("0.00 грн")
        font = QFont()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        self.labor_cost_label.setFont(font)
        self.labor_cost_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addRow("Работа:", self.labor_cost_label)

        return group

    def _create_cost_indicators_group(self):
        """Создание группы стоимостных показателей"""
        logger.debug("[ЦЕНА_ИНТЕРФЕЙС] Создание группы 'Стоимостные показатели'")
        group = QGroupBox("4. Стоимостные показатели")
        layout = QFormLayout(group)
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # --- Себестоимость ---
        self.prime_cost_label = QLabel("0.00 грн")
        font_bold = QFont()
        font_bold.setBold(True)
        self.prime_cost_label.setFont(font_bold)
        self.prime_cost_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addRow("Себестоимость:", self.prime_cost_label)

        # --- Накладные расходы ---
        overhead_layout = QHBoxLayout()
        self.overhead_percent_spinbox = QDoubleSpinBox()
        self.overhead_percent_spinbox.setRange(0.0, 200.0)
        self.overhead_percent_spinbox.setDecimals(2)
        self.overhead_percent_spinbox.setSuffix(" %")
        self.overhead_percent_spinbox.setValue(self._current_overhead_percent * 100)
        self.overhead_percent_spinbox.valueChanged.connect(self._on_overhead_changed)

        self.overhead_cost_label = QLabel("0.00 грн")
        self.overhead_cost_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.overhead_equal_label = QLabel("=")
        self.overhead_equal_label.setAlignment(Qt.AlignCenter)

        overhead_layout.addWidget(self.overhead_percent_spinbox)
        overhead_layout.addWidget(self.overhead_equal_label)
        overhead_layout.addWidget(self.overhead_cost_label)
        layout.addRow("Накладные расходы:", overhead_layout)

        # --- Прибыль ---
        profit_layout = QHBoxLayout()
        self.profit_percent_spinbox = QDoubleSpinBox()
        self.profit_percent_spinbox.setRange(0.0, 200.0)
        self.profit_percent_spinbox.setDecimals(2)
        self.profit_percent_spinbox.setSuffix(" %")
        self.profit_percent_spinbox.setValue(self._current_profit_percent * 100)
        self.profit_percent_spinbox.valueChanged.connect(self._on_profit_changed)

        self.profit_cost_label = QLabel("0.00 грн")
        self.profit_cost_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.profit_equal_label = QLabel("=")
        self.profit_equal_label.setAlignment(Qt.AlignCenter)

        profit_layout.addWidget(self.profit_percent_spinbox)
        profit_layout.addWidget(self.profit_equal_label)
        profit_layout.addWidget(self.profit_cost_label)
        layout.addRow("Прибыль:", profit_layout)

        # --- Расчетная цена ---
        calculated_price_layout = QVBoxLayout()

        self.calculated_price_label = QLabel("0.00 грн")
        font_large_bold = QFont()
        font_large_bold.setBold(True)
        font_large_bold.setPointSize(font_large_bold.pointSize() + 2)
        self.calculated_price_label.setFont(font_large_bold)
        self.calculated_price_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.calculated_price_label.setStyleSheet("color: blue;")

        self.approved_display_label = QLabel("")
        self.approved_display_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.approved_display_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")

        calculated_price_layout.addWidget(self.calculated_price_label)
        calculated_price_layout.addWidget(self.approved_display_label)

        layout.addRow("Расчетная цена изделия:", calculated_price_layout)

        # --- Утвержденная цена ---
        approved_price_layout = QHBoxLayout()
        self.approved_price_spinbox = QDoubleSpinBox()
        self.approved_price_spinbox.setRange(0.0, 10000000.0)
        self.approved_price_spinbox.setDecimals(2)
        self.approved_price_spinbox.setPrefix("₴ ")
        self.approved_price_spinbox.valueChanged.connect(self._on_approved_price_changed)
        self.approved_price_spinbox.setFixedWidth(150)

        approved_price_layout.addWidget(self.approved_price_spinbox)
        approved_price_layout.addStretch(1)
        layout.addRow("Утвержденная цена изделия:", approved_price_layout)

        return group

    def set_product(self, product_id):
        """Установка изделия для отображения цены"""
        logger.info(f"[ЦЕНА_ИНТЕРФЕЙС] === УСТАНОВКА ИЗДЕЛИЯ ID {product_id} ДЛЯ ВКЛАДКИ 'ЦЕНА ИЗДЕЛИЯ' ===")
        self.current_product_id = product_id
        self.update_pricing()

    def update_pricing(self):
        """Обновление расчета цены (с сохранением утвержденной из базы)"""
        logger.info(f"[ЦЕНА_ИНТЕРФЕЙС] === НАЧАЛО ОБНОВЛЕНИЯ РАСЧЕТА ЦЕНЫ ДЛЯ ИЗДЕЛИЯ ID {self.current_product_id} ===")
        if not self.current_product_id:
            self._clear_ui()
            self._set_fields_enabled(False)
            return

        try:
            # Сохраняем текущую утвержденную цену из базы перед пересчетом
            query = "SELECT approved_price FROM products WHERE id = ?"
            result = self.db_manager.fetch_one(query, (self.current_product_id,))
            db_approved_price = result[0] if result and result[0] is not None else None

            # Получаем новые расчетные данные
            pricing_data = self.pricing_manager.calculate_pricing(self.current_product_id)
            if not pricing_data:
                self._clear_ui()
                QMessageBox.critical(self, "Ошибка", "Не удалось рассчитать цену изделия.")
                return

            # Если утвержденная цена уже есть в БД — не затираем ее расчетной
            if db_approved_price and db_approved_price > 0:
                pricing_data["cost_indicators"]["approved_price"] = db_approved_price
            else:
                # По умолчанию утвержденная = расчетная при первом расчете
                pricing_data["cost_indicators"]["approved_price"] = pricing_data["cost_indicators"]["calculated_price"]

            # Обновляем интерфейс
            self._populate_ui(pricing_data)
            self._set_fields_enabled(True)
            logger.info(f"[ЦЕНА_ИНТЕРФЕЙС] Цена для изделия ID {self.current_product_id} успешно обновлена")

        except Exception as e:
            logger.error(f"[ЦЕНА_ИНТЕРФЕЙС] Ошибка при обновлении цены: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обновлении цены: {e}")
            self._set_fields_enabled(False)

    def _populate_ui(self, pricing_data):
        """Заполнение интерфейса данными"""
        logger.debug("[ЦЕНА_ИНТЕРФЕЙС] === ЗАПОЛНЕНИЕ UI ДАННЫМИ РАСЧЕТА ЦЕНЫ ===")

        # Блокируем обновления на время заполнения
        self._updating = True

        try:
            # 1. Общая информация
            product_info = pricing_data['product_info']
            self.article_label.setText(product_info.get('article', '-'))
            self.name_label.setText(product_info.get('name', '-'))
            self.total_weight_label.setText(f"{product_info.get('total_weight_kg', 0.0):.3f} кг")
            self.total_paint_area_label.setText(f"{product_info.get('total_paint_area_m2', 0.0):.3f} м²")

            # 2. Описание категорий материалов
            materials_summary = pricing_data['materials_summary']
            self.materials_table.setRowCount(len(materials_summary))
            for row, (category, data) in enumerate(materials_summary.items()):
                self.materials_table.setItem(row, 0, QTableWidgetItem(category))
                item_weight = QTableWidgetItem(f"{data['total_weight']:.3f}")
                item_weight.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.materials_table.setItem(row, 1, item_weight)

                item_cost = QTableWidgetItem(f"{data['total_cost']:.2f}")
                item_cost.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.materials_table.setItem(row, 2, item_cost)

            self.materials_table.resizeRowsToContents()

            # 3. Стоимость работ
            labor_cost = pricing_data['labor_cost']
            self.labor_cost_label.setText(f"{labor_cost:.2f} грн")

            # 4. Стоимостные показатели
            cost_indicators = pricing_data['cost_indicators']

            # Сохраняем текущие значения для пересчета
            self._current_prime_cost = cost_indicators['prime_cost']
            self._current_overhead_percent = cost_indicators['overhead_percent']
            self._current_profit_percent = cost_indicators['profit_percent']
            self._current_calculated_price = cost_indicators['calculated_price']
            self._current_approved_price = cost_indicators['approved_price']

            logger.debug(
                f"[ЦЕНА_ИНТЕРФЕЙС] Загружены цены: расчетная={self._current_calculated_price}, утвержденная={self._current_approved_price}")

            # Заполняем UI
            self.prime_cost_label.setText(f"{self._current_prime_cost:.2f} грн")

            self.overhead_percent_spinbox.setValue(self._current_overhead_percent * 100)
            overhead_cost = self._current_prime_cost * self._current_overhead_percent
            self.overhead_cost_label.setText(f"{overhead_cost:.2f} грн")

            profit_base = self._current_prime_cost + overhead_cost
            profit_cost = profit_base * self._current_profit_percent
            self.profit_cost_label.setText(f"{profit_cost:.2f} грн")

            # Установка утвержденной цены
            self.approved_price_spinbox.setValue(self._current_approved_price)

            # Обновляем отображение цен
            self._update_price_display(
                self._current_calculated_price,
                self._current_approved_price
            )

            logger.debug("[ЦЕНА_ИНТЕРФЕЙС] === ЗАПОЛНЕНИЕ UI ДАННЫМИ РАСЧЕТА ЦЕНЫ ЗАВЕРШЕНО ===")
        except Exception as e:
            logger.error(f"[ЦЕНА_ИНТЕРФЕЙС] Ошибка при заполнении UI данными расчета цены: {e}", exc_info=True)
        finally:
            # Разблокируем обновления
            self._updating = False

    def _clear_ui(self):
        """Очистка интерфейса"""
        logger.debug("[ЦЕНА_ИНТЕРФЕЙС] === ОЧИСТКА UI ВКЛАДКИ 'ЦЕНА ИЗДЕЛИЯ' ===")

        self.article_label.setText("-")
        self.name_label.setText("-")
        self.total_weight_label.setText("0.000 кг")
        self.total_paint_area_label.setText("0.000 м²")

        self.materials_table.setRowCount(0)

        self.labor_cost_label.setText("0.00 грн")

        self.prime_cost_label.setText("0.00 грн")
        self.overhead_percent_spinbox.setValue(55.0)
        self.overhead_cost_label.setText("0.00 грн")
        self.profit_percent_spinbox.setValue(30.0)
        self.profit_cost_label.setText("0.00 грн")
        self.calculated_price_label.setText("0.00 грн")
        self.approved_price_spinbox.setValue(0.0)
        self.approved_display_label.setText("")

        # Сброс внутренних переменных
        self._current_prime_cost = 0.0
        self._current_overhead_percent = 0.55
        self._current_profit_percent = 0.30
        self._current_calculated_price = 0.0
        self._current_approved_price = 0.0

        logger.debug("[ЦЕНА_ИНТЕРФЕЙС] === ОЧИСТКА UI ЗАВЕРШЕНА ===")

    def _set_fields_enabled(self, enabled):
        """Блокировка/разблокировка полей ввода"""
        logger.debug(f"[ЦЕНА_ИНТЕРФЕЙС] {'Разблокировка' if enabled else 'Блокировка'} полей ввода")
        self.overhead_percent_spinbox.setEnabled(enabled)
        self.profit_percent_spinbox.setEnabled(enabled)
        self.approved_price_spinbox.setEnabled(enabled)
        self.update_button.setEnabled(enabled)
        self.reset_approved_price_btn.setEnabled(enabled)
        self.apply_button.setEnabled(enabled)

    def _on_overhead_changed(self, value):
        """Обработчик изменения процента накладных расходов"""
        if self._updating:
            return
        logger.debug(f"[ЦЕНА_ИНТЕРФЕЙС] Изменение процента накладных расходов: {value}%")
        try:
            percent = value / 100.0
            overhead_cost = self._current_prime_cost * percent
            self.overhead_cost_label.setText(f"{overhead_cost:.2f} грн")
            self._recalculate_price()
        except Exception as e:
            logger.error(f"[ЦЕНА_ИНТЕРФЕЙС] Ошибка при изменении накладных расходов: {e}")

    def _on_profit_changed(self, value):
        """Обработчик изменения процента прибыли"""
        if self._updating:
            return
        logger.debug(f"[ЦЕНА_ИНТЕРФЕЙС] Изменение процента прибыли: {value}%")
        try:
            percent = value / 100.0
            profit_base = self._current_prime_cost + (
                        self._current_prime_cost * self.overhead_percent_spinbox.value() / 100.0)
            profit_cost = profit_base * percent
            self.profit_cost_label.setText(f"{profit_cost:.2f} грн")
            self._recalculate_price()
        except Exception as e:
            logger.error(f"[ЦЕНА_ИНТЕРФЕЙС] Ошибка при изменении прибыли: {e}")

    def _on_approved_price_changed(self, value):
        """Обработчик изменения утвержденной цены"""
        if self._updating:
            return
        logger.debug(f"[ЦЕНА_ИНТЕРФЕЙС] Изменение утвержденной цены: {value} грн")
        self._current_approved_price = value
        self._update_price_display(self._current_calculated_price, value)

    def _update_price_display(self, calculated_price, approved_price):
        """Обновление отображения цен с учетом различий"""
        logger.debug(
            f"[ЦЕНА_ИНТЕРФЕЙС] Обновление отображения цен: расчетная={calculated_price}, утвержденная={approved_price}")

        # Отображаем расчетную цену
        self.calculated_price_label.setText(f"{calculated_price:.2f} грн")

        # Проверяем, отличаются ли цены (с учетом погрешности округления)
        price_difference = abs(calculated_price - approved_price) > 0.01

        if price_difference and approved_price > 0:
            # Если цены отличаются и утвержденная цена установлена
            font = self.calculated_price_label.font()
            font.setStrikeOut(True)
            self.calculated_price_label.setFont(font)
            self.calculated_price_label.setStyleSheet("color: gray; text-decoration: line-through;")

            # Показываем утвержденную цену рядом
            self.approved_display_label.setText(f"✓ {approved_price:.2f} грн")
            self.approved_display_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
            logger.debug(
                f"[ЦЕНА_ИНТЕРФЕЙС] Цены отличаются: расчетная={calculated_price}, утвержденная={approved_price}")
        else:
            # Если цены совпадают или утвержденная цена не установлена
            font = self.calculated_price_label.font()
            font.setStrikeOut(False)
            self.calculated_price_label.setFont(font)
            self.calculated_price_label.setStyleSheet("color: blue;")

            self.approved_display_label.setText("")
            logger.debug(f"[ЦЕНА_ИНТЕРФЕЙС] Цены совпадают или утвержденная не установлена")

    def _recalculate_price(self):
        """Пересчет итоговой цены"""
        if self._updating:
            return
        logger.debug("[ЦЕНА_ИНТЕРФЕЙС] Пересчет итоговой цены")
        try:
            prime_cost = self._current_prime_cost
            overhead_cost = prime_cost * (self.overhead_percent_spinbox.value() / 100.0)
            profit_base = prime_cost + overhead_cost
            profit_cost = profit_base * (self.profit_percent_spinbox.value() / 100.0)
            calculated_price = prime_cost + overhead_cost + profit_cost

            self.overhead_cost_label.setText(f"{overhead_cost:.2f} грн")
            self.profit_cost_label.setText(f"{profit_cost:.2f} грн")
            self.calculated_price_label.setText(f"{calculated_price:.2f} грн")

            self._current_calculated_price = calculated_price

            # Обновляем отображение
            self._update_price_display(calculated_price, self.approved_price_spinbox.value())

            logger.debug(
                f"[ЦЕНА_ИНТЕРФЕЙС] Пересчитана цена: {calculated_price:.2f}, утвержденная: {self.approved_price_spinbox.value():.2f}")

        except Exception as e:
            logger.error(f"[ЦЕНА_ИНТЕРФЕЙС] Ошибка при пересчете цены: {e}")

    def _on_update_clicked(self):
        """Обработчик нажатия кнопки 'Обновить'"""
        logger.info("[ЦЕНА_ИНТЕРФЕЙС] Нажата кнопка 'Обновить'")
        try:
            self.update_pricing()
            QMessageBox.information(self, "Успех", "Расчет цены обновлен (утвержденная цена сохранена).")
        except Exception as e:
            logger.error(f"[ЦЕНА_ИНТЕРФЕЙС] Ошибка при обновлении: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обновлении расчета цены:\n{e}")

    def _on_reset_approved_price(self):
        """Сброс утвержденной цены на расчетную"""
        logger.debug("[ЦЕНА_ИНТЕРФЕЙС] Сброс утвержденной цены на расчетную")
        self.approved_price_spinbox.setValue(self._current_calculated_price)
        self._update_price_display(self._current_calculated_price, self._current_calculated_price)
        QMessageBox.information(self, "Успех", "Утвержденная цена сброшена на расчетную")

    def update_price_display(self, calculated_price, approved_price):
        """
        Публичный метод для обновления отображения расчетной и утвержденной цены.
        Вызывается из других модулей (например, при изменении операции).
        """
        try:
            self._current_calculated_price = calculated_price
            self._current_approved_price = approved_price
            self._update_price_display(calculated_price, approved_price)
            logger.info(
                f"[ЦЕНА_ИНТЕРФЕЙС] Обновлено отображение цен: расчетная={calculated_price}, утвержденная={approved_price}")
        except Exception as e:
            logger.error(f"[ЦЕНА_ИНТЕРФЕЙС] Ошибка при обновлении отображения цены: {e}", exc_info=True)

