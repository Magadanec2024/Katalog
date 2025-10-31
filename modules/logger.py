# modules/logger.py
import logging
import os
from datetime import datetime

# Убедимся, что директория для логов существует
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Настройка логгера
logger = logging.getLogger("ProductCalculator")
logger.setLevel(logging.DEBUG)

# Создаем обработчик для записи в файл
file_handler = logging.FileHandler(os.path.join(log_dir, "app.log"), encoding='utf-8')
file_handler.setLevel(logging.DEBUG)

# Создаем обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO) # В консоль пойдут только INFO и выше

# Создаем форматтер и добавляем его к обработчикам
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Добавляем обработчики к логгеру
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Отключаем propagate, чтобы избежать дублирования сообщений
# если логгер вызывается из других модулей
logger.propagate = False

def get_logger():
    """Возвращает настроенный логгер."""
    return logger

# Запишем стартовое сообщение
logger.info("=" * 50)
logger.info("ЗАПУСК ПРИЛОЖЕНИЯ")
logger.info("=" * 50)