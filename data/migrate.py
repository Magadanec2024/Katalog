import sqlite3

db_path = "database.db"

queries = [
    "ALTER TABLE products ADD COLUMN total_paint_area REAL DEFAULT 0.0;",
    "ALTER TABLE product_materials ADD COLUMN paint_area REAL DEFAULT 0.0;",
]

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
for q in queries:
    try:
        cursor.execute(q)
        print(f"✅ Выполнено: {q}")
    except sqlite3.OperationalError as e:
        print(f"⚠️ Пропущено: {e}")
conn.commit()
conn.close()
print("Миграция завершена.")
