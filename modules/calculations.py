# modules/calculations.py
from modules.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)


class CalculationManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def calculate_operation_cost(self, quantity_measured, time_measured, rate_per_minute):
        """Расчет стоимости операции"""
        if quantity_measured == 0:
            return 0.0
        time_per_unit = time_measured / quantity_measured
        return time_per_unit * rate_per_minute

    def calculate_material_cost(self, material_id, length=0, width=0, thickness=0, quantity=0,
                                material_type='length_quantity'):
        """Расчет стоимости материала в зависимости от типа"""
        material = self.db_manager.fetch_one(
            "SELECT weight_per_meter, final_price_kg FROM materials WHERE id = ?",
            (material_id,)
        )

        if not material:
            return 0.0

        weight_per_meter, final_price_kg = material

        if material_type == 'length_quantity':
            # Материал с длиной и количеством (трубы, проволока, прутки)
            total_weight = length * quantity * weight_per_meter
            return total_weight * final_price_kg

        elif material_type == 'dimensions':
            # Материал с размерами (листовые)
            # Для упрощения - используем объемный расчет
            # В реальности может потребоваться более сложная логика
            density = 7850  # плотность стали в кг/м3
            volume = length * width * thickness * quantity  # в м3
            weight = volume * density
            return weight * final_price_kg

        elif material_type == 'quantity_only':
            # Метизы - расчет по цене за единицу
            # В этом случае final_price_kg может быть ценой за единицу
            return quantity * final_price_kg

        else:
            return 0.0

    def get_product_totals(self, product_id):
        """Получение итогов по изделию"""
        # Сумма по операциям
        operations_total = self.db_manager.fetch_one(
            "SELECT SUM(cost) FROM operations WHERE product_id = ?",
            (product_id,)
        )[0] or 0.0

        # Сумма по материалам
        materials_total = self.db_manager.fetch_one(
            "SELECT SUM(cost) FROM product_materials WHERE product_id = ?",
            (product_id,)
        )[0] or 0.0

        return {
            'operations_total': operations_total,
            'materials_total': materials_total,
            'total_cost': operations_total + materials_total
        }

    def calculate_pricing(self, product_id, overhead_rate=0.55, profit_rate=0.30):
        """Расчет цены изделия с накладными расходами и прибылью"""
        totals = self.get_product_totals(product_id)

        overhead_cost = totals['total_cost'] * overhead_rate
        profit_cost = (totals['total_cost'] + overhead_cost) * profit_rate
        final_price = totals['total_cost'] + overhead_cost + profit_cost

        return {
            'base_cost': totals['total_cost'],
            'overhead_cost': overhead_cost,
            'profit_cost': profit_cost,
            'final_price': final_price,
            'overhead_rate': overhead_rate,
            'profit_rate': profit_rate
        }
