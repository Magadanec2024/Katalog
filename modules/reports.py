# modules/reports.py
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from modules.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)


class ReportManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def export_product_to_excel(self, product_id, file_path):
        """Экспорт изделия в Excel с форматированием"""
        try:
            product_info = self.db_manager.fetch_one(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            )

            operations = self.db_manager.fetch_all("""
                SELECT o.operation_name, o.quantity_measured, o.time_measured,
                       o.time_per_unit, o.rate_per_minute, o.cost, e.name as employee_name, o.approved_rate
                FROM operations o
                LEFT JOIN employees e ON o.employee_id = e.id
                WHERE o.product_id = ?
            """, (product_id,))

            materials = self.db_manager.fetch_all("""
                SELECT m.name, pm.length, pm.width, pm.quantity, pm.cost
                FROM product_materials pm
                JOIN materials m ON pm.material_id = m.id
                WHERE pm.product_id = ?
            """, (product_id,))

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Лист с информацией об изделии
                info_df = pd.DataFrame([{
                    'ID': product_info[1],
                    'Артикул': product_info[2],
                    'Название': product_info[3]
                }])
                info_df.to_excel(writer, sheet_name='Информация', index=False)
                # Убедимся, что лист "Информация" видим (по умолчанию он первый и видимый)

                # Лист с операциями
                if operations:
                    ops_df = pd.DataFrame(operations, columns=[
                        'Операция', 'Кол-во замеров', 'Время замера',
                        'Время на ед.', 'Ставка', 'Стоимость', 'Сотрудник', 'Утверждённая расценка'
                    ])
                    ops_df.to_excel(writer, sheet_name='Операции', index=False)
                    worksheet = writer.sheets['Операции']
                    for col in worksheet.columns:
                        max_length = 0
                        column = col[0].column_letter
                        for cell in col:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = (max_length + 2)
                        worksheet.column_dimensions[column].width = adjusted_width

                # Лист с материалами
                if materials:
                    mats_df = pd.DataFrame(materials, columns=[
                        'Материал', 'Длина', 'Ширина', 'Количество', 'Стоимость'
                    ])
                    mats_df.to_excel(writer, sheet_name='Материалы', index=False)
                    worksheet = writer.sheets['Материалы']
                    for col in worksheet.columns:
                        max_length = 0
                        column = col[0].column_letter
                        for cell in col:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = (max_length + 2)
                        worksheet.column_dimensions[column].width = adjusted_width

            return True
        except Exception as e:
            logger.error(f"Ошибка при экспорте в Excel: {e}", exc_info=True)
            return False

    def export_product_to_pdf(self, product_id, file_path):
        """Экспорт изделия в PDF"""
        try:
            product_info = self.db_manager.fetch_one(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            )

            operations = self.db_manager.fetch_all("""
                SELECT o.operation_name, o.quantity_measured, o.time_measured,
                       o.time_per_unit, o.rate_per_minute, o.cost, e.name as employee_name
                FROM operations o
                LEFT JOIN employees e ON o.employee_id = e.id
                WHERE o.product_id = ?
            """, (product_id,))

            materials = self.db_manager.fetch_all("""
                SELECT m.name, pm.length, pm.quantity, pm.cost
                FROM product_materials pm
                JOIN materials m ON pm.material_id = m.id
                WHERE pm.product_id = ?
            """, (product_id,))

            doc = SimpleDocTemplate(file_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []

            title = Paragraph(f"Карточка изделия: {product_info[3]}", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))

            info_text = f"""
            ID: {product_info[1]}<br/>
            Артикул: {product_info[2]}<br/>
            Название: {product_info[3]}<br/>
            """
            info_para = Paragraph(info_text, styles['Normal'])
            story.append(info_para)
            story.append(Spacer(1, 12))

            if operations:
                story.append(Paragraph("Технологические операции:", styles['Heading2']))
                ops_data = [['Операция', 'Кол-во', 'Время', 'Ставка', 'Стоимость', 'Сотрудник']]
                for op in operations:
                    ops_data.append([
                        str(op[0]), str(op[1]), f"{op[2]:.2f}", f"{op[4]:.2f}", f"{op[5]:.2f}", str(op[6] or '')
                    ])
                ops_table = Table(ops_data)
                ops_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(ops_table)
                story.append(Spacer(1, 12))

            if materials:
                story.append(Paragraph("Материалы:", styles['Heading2']))
                mats_data = [['Материал', 'Длина', 'Количество', 'Стоимость']]
                for mat in materials:
                    mats_data.append([
                        str(mat[0]), f"{mat[1]:.3f}", str(mat[2]), f"{mat[3]:.2f}"
                    ])
                mats_table = Table(mats_data)
                mats_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(mats_table)
                story.append(Spacer(1, 12))

            doc.build(story)
            return True
        except Exception as e:
            logger.error(f"Ошибка при экспорте в PDF: {e}", exc_info=True)
            return False
