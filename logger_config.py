import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger():
    """
    Настраивает логирование для записи в файл bot.log с ротацией.
    """
    # Создаем директорию для логов, если она не существует
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, 'bot.log')

    # Создаем RotatingFileHandler с ротацией при достижении 10MB, сохраняя 5 резервных копий
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )

    # Форматирование логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Настраиваем корневой логгер
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Логируем INFO и выше
    logger.addHandler(handler)

    return logger

# Создаем логгер при импорте модуля
logger = setup_logger()
