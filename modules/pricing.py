# modules/pricing.py
import logging
import math
from collections import defaultdict
from typing import Dict, Any, List, Optional

from modules.database import DatabaseManager

logger = logging.getLogger(__name__)


class PricingManager:
    """
    Менеджер расчёта цены изделия.
    Включает расчет материалов, работ, площади покраски и стоимости краски.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    # -----------------------
    # Внешняя точка входа
    # -----------------------
    def calculate_pricing(self, product_id: int,
                          paint_consumption_kg_per_m2_per_layer: float = 0.10,
                          layers: int = 2,
                          loss_coeff: float = 1.10,
                          use_loss_coeff: bool = True) -> Optional[Dict[str, Any]]:
        """
        Основной метод. Возвращает структуру pricing_data или None при ошибке.
        Включает вычисление площади покраски и стоимости краски (если в составе есть материал 'краска'/'лак').
        """
        logger.info(f"[ЦЕНА_БД] === НАЧАЛО РАСЧЕТА ЦЕНЫ ИЗД. ID {product_id} ===")
        try:
            pricing_data: Dict[str, Any] = {}

            # 1) Получить product_info
            product_row = self.db_manager.fetch_one("SELECT * FROM products WHERE id = ?", (product_id,))
            if not product_row:
                logger.error(f"[ЦЕНА_БД] Изделие ID {product_id} не найдено")
                return None

            # product_row - кортеж, порядок полей зависит от DDL; доступ через индексы оставляем как раньше
            # Безопасно читаем предполагаемые поля (порядок в вашем проекте соответствует предыдущей версии)
            product_id_field = product_row[1] if len(product_row) > 1 else None
            article = product_row[2] if len(product_row) > 2 else ""
            name = product_row[3] if len(product_row) > 3 else ""

            # считываем сохраненные коэффициенты — если отсутствуют, используем дефолты
            def _safe_float_from_row(row, idx, default):
                try:
                    return float(row[idx]) if len(row) > idx and row[idx] is not None else default
                except Exception:
                    return default

            overhead_percent_saved = _safe_float_from_row(product_row, 4, 0.55)
            profit_percent_saved = _safe_float_from_row(product_row, 5, 0.30)
            approved_price_saved = _safe_float_from_row(product_row, 6, 0.0)

            pricing_data['product_info'] = {
                'product_id': product_id_field,
                'article': article,
                'name': name,
                'total_weight_kg': 0.0,
                'total_paint_area_m2': 0.0
            }

            # 2) Материалы изделия — получаем нужные поля
            # Здесь выбираем те поля, которые в вашем проекте используются: category, pm.length, pm.width, pm.thickness, pm.quantity, pm.cost, m.name, m.weight_per_meter, pm.material_id
            materials_rows = self.db_manager.fetch_all("""
                SELECT 
                    COALESCE(m.category, '') as category,
                    COALESCE(pm.length, 0.0) as length_mm,
                    COALESCE(pm.width, 0.0) as width_mm,
                    COALESCE(pm.thickness, 0.0) as thickness_mm,
                    COALESCE(pm.quantity, 0) as quantity,
                    COALESCE(pm.cost, 0.0) as cost,
                    COALESCE(m.name, '') as material_name,
                    COALESCE(m.weight_per_meter, 0.0) as weight_per_meter,
                    pm.material_id as material_id,
                    COALESCE(m.diameter, 0.0) as diameter_mm,
                    COALESCE(m.section_length, 0.0) as section_length_mm,
                    COALESCE(m.section_width, 0.0) as section_width_mm,
                    COALESCE(m.our_price_per_kg, m.final_price_kg, 0.0) as price_per_kg
                FROM product_materials pm
                JOIN materials m ON pm.material_id = m.id
                WHERE pm.product_id = ?
                ORDER BY m.category, m.name
            """, (product_id,))

            # Преобразуем строки в упорядоченный список словарей для дальнейших расчетов
            product_materials: List[Dict[str, Any]] = []
            for row in materials_rows or []:
                # row соответствует полям в SELECT выше
                (category, length_mm, width_mm, thickness_mm, quantity, cost, material_name,
                 weight_per_meter, material_id, diameter_mm, section_length_mm, section_width_mm,
                 price_per_kg) = row
                product_materials.append({
                    'category': category,
                    'length_mm': float(length_mm),
                    'width_mm': float(width_mm),
                    'thickness_mm': float(thickness_mm),
                    'quantity': int(quantity),
                    'cost': float(cost),
                    'name': material_name,
                    'weight_per_meter': float(weight_per_meter),
                    'material_id': material_id,
                    'diameter_mm': float(diameter_mm),
                    'section_length_mm': float(section_length_mm),
                    'section_width_mm': float(section_width_mm),
                    'price_per_kg': float(price_per_kg)
                })

            # 2.1 Суммируем материалы по категориям и считаем вес/стоимость (и предварительную площадь покраски)
            materials_summary = self._summarize_materials_from_list(product_materials)
            pricing_data['materials_summary'] = materials_summary

            # Заполняем total_weight и preliminary paint area (сейчас в м^2)
            total_weight = sum(cat['total_weight'] for cat in materials_summary.values())
            preliminary_paint_area = sum(cat['total_paint_area'] for cat in materials_summary.values())
            pricing_data['product_info']['total_weight_kg'] = round(total_weight, 3)
            pricing_data['product_info']['total_paint_area_m2'] = round(preliminary_paint_area, 3)

            # 3) Операции (работы)
            ops_rows = self.db_manager.fetch_all("""
                SELECT 
                    COALESCE(o.operation_name, ''),
                    COALESCE(o.quantity_measured, 0),
                    COALESCE(o.time_measured, 0.0),
                    COALESCE(o.time_per_unit, 0.0),
                    COALESCE(o.rate_per_minute, 0.0),
                    COALESCE(o.cost, 0.0),
                    COALESCE(e.name, ''),
                    COALESCE(o.approved_rate, '')
                FROM operations o
                LEFT JOIN employees e ON o.employee_id = e.id
                WHERE o.product_id = ?
                ORDER BY o.id
            """, (product_id,))

            labor_cost = self._calculate_labor_cost_from_db(ops_rows)
            pricing_data['labor_cost'] = labor_cost

            # 4) Стоимостные показатели (пока без учета краски)
            cost_indicators = self._calculate_cost_indicators(
                labor_cost,
                materials_summary,
                overhead_percent_saved,
                profit_percent_saved,
                approved_price_saved
            )
            pricing_data['cost_indicators'] = cost_indicators

            # 5) Площадь покраски + стоимость краски (если есть материал 'краска'/'лак'):
            pricing_data['product_materials'] = product_materials  # для функции apply_paint_costs_to_pricing
            pricing_data = self.apply_paint_costs_to_pricing(
                pricing_data,
                paint_consumption_kg_per_m2_per_layer=paint_consumption_kg_per_m2_per_layer,
                layers=layers,
                loss_coeff=loss_coeff,
                use_loss_coeff=use_loss_coeff
            )

            # 6) Попытка записать total_paint_area в products (если колонка есть)
            try:
                total_area = pricing_data.get('product_info', {}).get('total_paint_area_m2', 0.0)
                self.db_manager.execute_query("UPDATE products SET total_paint_area = ? WHERE id = ?", (total_area, product_id))
            except Exception:
                # Если такой колонки нет — не критично, логируем
                logger.debug("[ЦЕНА_БД] Не удалось записать total_paint_area в products (возможно, колонка отсутствует)")

            logger.info(f"[ЦЕНА_БД] === РАСЧЕТ ЦЕНЫ ИЗД. ID {product_id} ЗАВЕРШЕН УСПЕШНО ===")
            logger.debug(f"[ЦЕНА_БД] Итоговые данные pricing: {pricing_data}")
            return pricing_data

        except Exception as e:
            logger.error(f"[ЦЕНА_БД] === КРИТИЧЕСКАЯ ОШИБКА ПРИ РАСЧЕТЕ ЦЕНЫ: {e} ===", exc_info=True)
            return None

    # -----------------------
    # Вспомогательные методы
    # -----------------------
    def _summarize_materials_from_list(self, product_materials: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        Суммирует материалы по категории и рассчитывает:
            - total_weight (kg)
            - total_cost (currency)
            - total_paint_area (m2) (предварительный; для листов и профилей)
        Возвращает dict {category: {total_weight, total_cost, total_paint_area}}
        """
        logger.debug("[ЦЕНА_БД] === СУММИРОВАНИЕ МАТЕРИАЛОВ (Список) ===")
        summary = defaultdict(lambda: {'total_weight': 0.0, 'total_cost': 0.0, 'total_paint_area': 0.0})

        for m in product_materials:
            try:
                cat = (m.get('category') or 'Без категории')
                length_mm = float(m.get('length_mm') or 0.0)
                width_mm = float(m.get('width_mm') or 0.0)
                thickness_mm = float(m.get('thickness_mm') or 0.0)
                qty = int(m.get('quantity') or 0)
                cost = float(m.get('cost') or 0.0)
                name = m.get('name') or ''
                weight_per_meter = float(m.get('weight_per_meter') or 0.0)

                # Вес: length (в метрах) * weight_per_meter * qty
                length_m = length_mm / 1000
                weight = length_m * weight_per_meter * qty
                summary[cat]['total_weight'] += weight
                summary[cat]['total_cost'] += cost

                # Предварительная площадь покраски: используем упрощённую логику
                # - если есть width_mm (>0) — считаем площадь L * W * кол-во (две стороны для листов)
                # - иначе используем профильную аппроксимацию (см. calculate_paint_area_for_material дальше)
                paint_area = 0.0
                if width_mm and width_mm > 0:
                    # лист или профиль с заданной шириной — считаем площадь одной стороны * 2 (две стороны)
                    paint_area = (length_mm / 1000.0) * (width_mm / 1000.0) * 2.0 * qty
                else:
                    # попробуем расчет по диаметру/сечению (если есть)
                    paint_area = self.calculate_paint_area_for_material(m, length_mm, qty)

                summary[cat]['total_paint_area'] += paint_area

            except Exception as e:
                logger.warning(f"[ЦЕНА_БД] Ошибка при обработке материала {m}: {e}", exc_info=True)
                continue

        # Округляем итог
        result = {}
        for cat, vals in summary.items():
            result[cat] = {
                'total_weight': round(vals['total_weight'], 3),
                'total_cost': round(vals['total_cost'], 2),
                'total_paint_area': round(vals['total_paint_area'], 3)
            }
        logger.debug(f"[ЦЕНА_БД] Сводка материалов: {result}")
        return result

    def _calculate_labor_cost_from_db(self, operations_data: List[tuple]) -> float:
        """
        Рассчитывает суммарную стоимость работ, используя утверждённую расценку (approved_rate),
        если она указана, иначе использует рассчитанную стоимость (поле cost).
        """
        logger.debug("[ЦЕНА_БД] === РАСЧЕТ СТОИМОСТИ РАБОТ (ОПЕРАЦИИ) ===")
        total = 0.0
        for op in operations_data or []:
            try:
                operation_name = str(op[0] or "")
                quantity_measured = int(op[1] or 0)
                time_measured = float(op[2] or 0.0)
                time_per_unit = float(op[3] or 0.0)
                rate_per_minute = float(op[4] or 0.0)
                calculated_cost = float(op[5] or 0.0)
                # employee_name = str(op[6] or "")  # не нужен для расчёта здесь
                approved_rate_raw = op[7]

                if approved_rate_raw is not None and str(approved_rate_raw).strip() != "" and str(approved_rate_raw).strip().lower() != "none":
                    try:
                        approved_val = float(approved_rate_raw)
                        # approved_rate у вас в проекте трактуется как абсолютная сумма по операции
                        total += approved_val
                        logger.debug(f"[ЦЕНА_БД] Операция '{operation_name}': взята утвержденная расценка {approved_val:.2f}")
                    except Exception:
                        total += calculated_cost
                        logger.debug(f"[ЦЕНА_БД] Операция '{operation_name}': некорректная утвержденная расценка, взята расчетная {calculated_cost:.2f}")
                else:
                    total += calculated_cost
                    logger.debug(f"[ЦЕНА_БД] Операция '{operation_name}': взята расчетная стоимость {calculated_cost:.2f}")

            except Exception as e:
                logger.warning(f"[ЦЕНА_БД] Пропущена операция из-за ошибки: {e}", exc_info=True)
                continue

        logger.debug(f"[ЦЕНА_БД] Итоговая стоимость работ: {total:.2f}")
        return round(total, 2)

    def _calculate_cost_indicators(self, labor_cost: float, materials_summary: Dict[str, Dict[str, float]],
                                   overhead_percent: float = 0.55, profit_percent: float = 0.30,
                                   approved_price: float = 0.0) -> Dict[str, Any]:
        """
        Рассчитывает prime_cost, overhead, profit, calculated_price и возвращает словарь indicators.
        approved_price: если 0 — считаем новое изделие и approved := calculated; иначе используем существующее.
        """
        logger.debug("[ЦЕНА_БД] === РАСЧЕТ СТОИМОСТНЫХ ПОКАЗАТЕЛЕЙ ===")
        total_material_cost = sum((v.get('total_cost', 0.0) for v in materials_summary.values()))
        prime_cost = labor_cost + total_material_cost
        overhead_cost = prime_cost * overhead_percent
        profit_cost = (prime_cost + overhead_cost) * profit_percent
        calculated_price = prime_cost + overhead_cost + profit_cost

        if approved_price == 0.0:
            final_approved = calculated_price
        else:
            final_approved = approved_price

        indicators = {
            'prime_cost': round(prime_cost, 2),
            'overhead_percent': overhead_percent,
            'overhead_cost': round(overhead_cost, 2),
            'profit_percent': profit_percent,
            'profit_cost': round(profit_cost, 2),
            'calculated_price': round(calculated_price, 2),
            'approved_price': round(final_approved, 2),
            'total_material_cost': round(total_material_cost, 2)
        }
        logger.debug(f"[ЦЕНА_БД] Indicators: {indicators}")
        return indicators

    # -----------------------
    # Площадь покраски и краска
    # -----------------------
    @staticmethod
    def calculate_paint_area_for_material(material_row: Dict[str, Any], length_mm: float, quantity: int = 1) -> float:
        """
        Рассчитать площадь покраски (м²) для одной позиции материала (всего по quantity).
        Поддерживает:
          - диаметр (мм) -> боковая поверхность цилиндра: π * D * L
          - section_length_mm, section_width_mm -> профиль прямоугольный: perimeter * L
          - листы (category содержит 'лист'/'дсп'/'мдф') -> L * W * 2 (обе стороны)
        length_mm в мм.
        Возвращает площадь в м² (для всей позиции, с учётом quantity).
        """
        try:
            diameter = float(material_row.get('diameter_mm') or 0.0)
            a_mm = float(material_row.get('section_length_mm') or 0.0)
            b_mm = float(material_row.get('section_width_mm') or 0.0)
            category = (material_row.get('category') or '').lower()

            L_m = (length_mm or 0.0) / 1000.0
            if L_m <= 0:
                return 0.0

            area_per_piece = 0.0

            # Круглый профиль
            if diameter > 0:
                D_m = diameter / 1000.0
                area_per_piece = math.pi * D_m * L_m  # поверхность боковая
            # Прямоугольный профиль
            elif a_mm > 0 and b_mm > 0:
                a_m = a_mm / 1000.0
                b_m = b_mm / 1000.0
                perimeter = 2.0 * (a_m + b_m)
                area_per_piece = perimeter * L_m
            # Лист
            elif any(k in category for k in ['лист', 'дсп', 'мдф', 'панель']):
                # пытаемся взять width_mm из section_width_mm или length_mm param
                w_mm = a_mm or b_mm
                if w_mm > 0:
                    W_m = w_mm / 1000.0
                    area_per_piece = L_m * W_m * 2.0  # обе стороны
                else:
                    area_per_piece = 0.0
            else:
                # Неизвестная геометрия
                area_per_piece = 0.0

            total_area = area_per_piece * (quantity or 1)
            return total_area

        except Exception as e:
            logger.error(f"[ЦЕНА_БД] Ошибка calculate_paint_area_for_material: {e}", exc_info=True)
            return 0.0

    def apply_paint_costs_to_pricing(self, pricing_data: Dict[str, Any],
                                     paint_consumption_kg_per_m2_per_layer: float = 0.10,
                                     layers: int = 2,
                                     loss_coeff: float = 1.10,
                                     use_loss_coeff: bool = True) -> Dict[str, Any]:
        """
        Рассчитывает общую площадь покраски, потребность краски (кг) и её стоимость.
        Изменяет pricing_data: добавляет pricing_data['product_info']['total_paint_area_m2'],
        pricing_data['paint'] = {'required_kg', 'cost', 'material_id'} и увеличивает cost_indicators accordingly.
        """
        try:
            mats = pricing_data.get('product_materials', [])
            total_area = 0.0
            for m in mats:
                length_mm = float(m.get('length_mm') or 0.0)
                qty = int(m.get('quantity') or 1)
                area = self.calculate_paint_area_for_material(m, length_mm, qty)
                m['paint_area'] = round(area, 6)
                total_area += area

            pricing_data.setdefault('product_info', {})
            pricing_data['product_info']['total_paint_area_m2'] = round(total_area, 3)

            # Найти материал-краску среди материалов изделия
            paint_mat = None
            for m in mats:
                name = (m.get('name') or '').lower()
                cat = (m.get('category') or '').lower()
                if 'краска' in name or 'краска' in cat or 'лак' in name or 'лак' in cat:
                    paint_mat = m
                    break

            paint_info = {'required_kg': 0.0, 'cost': 0.0, 'material_id': None}
            if paint_mat:
                required_kg = total_area * paint_consumption_kg_per_m2_per_layer * layers
                if use_loss_coeff:
                    required_kg *= loss_coeff
                price_kg = float(paint_mat.get('price_per_kg') or paint_mat.get('price_per_kg', 0.0) or paint_mat.get('price_per_kg', 0.0) or paint_mat.get('price_per_kg', 0.0) or paint_mat.get('price_per_kg', 0.0) or paint_mat.get('price_per_kg', 0.0) or paint_mat.get('price_per_kg', 0.0) or paint_mat.get('price_per_kg', 0.0) or paint_mat.get('price_per_kg', 0.0) or paint_mat.get('price_per_kg', 0.0))
                # fallback на price_per_kg или price_per_kg synonyms
                if not price_kg:
                    price_kg = float(m.get('price_per_kg') or m.get('Наша продажа/кг') or 0.0)

                paint_cost = required_kg * price_kg
                paint_info['required_kg'] = round(required_kg, 3)
                paint_info['cost'] = round(paint_cost, 2)
                paint_info['material_id'] = paint_mat.get('material_id') or paint_mat.get('id')

                # Добавляем стоимость краски в материалы и себестоимость
                if 'cost_indicators' in pricing_data:
                    pricing_data['cost_indicators']['total_material_cost'] = round(
                        pricing_data['cost_indicators'].get('total_material_cost', 0.0) + paint_cost, 2)
                    pricing_data['cost_indicators']['prime_cost'] = round(
                        pricing_data['cost_indicators'].get('prime_cost', 0.0) + paint_cost, 2)

                pricing_data['paint'] = paint_info
            else:
                logger.info("[ЦЕНА_БД] Краска не найдена среди материалов изделия — расход краски не рассчитан")

            return pricing_data

        except Exception as e:
            logger.error(f"[ЦЕНА_БД] Ошибка apply_paint_costs_to_pricing: {e}", exc_info=True)
            return pricing_data
