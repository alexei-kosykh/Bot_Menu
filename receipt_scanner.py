"""
Модуль для распознавания чеков
Поддерживает три метода:
1. Декодирование QR-кода
2. Получение данных через API ФНС
3. OCR-распознавание текста (запасной вариант)
"""

import re
from io import BytesIO
from datetime import datetime
import logger_config

# Try to import image processing libraries
IMAGE_PROCESSING_AVAILABLE = False

try:
    from PIL import Image
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    print("Предупреждение: Библиотека PIL не установлена")
    IMAGE_PROCESSING_AVAILABLE = False

try:
    from pyzbar import pyzbar
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("⚠️  Библиотека pyzbar не установлена. QR-коды не будут распознаваться.")
    print("   Установка: pip install pyzbar")
    print("   Требуется системная библиотека zbar")
except Exception as e:
    QR_AVAILABLE = False
    print(f"⚠️  Ошибка загрузки pyzbar: {e}")
    print("   QR-коды не будут распознаваться.")

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️  Библиотека pytesseract не установлена. OCR-распознавание текста недоступно.")
    print("   Установка: pip install pytesseract")
    print("   Требуется Tesseract OCR: https://github.com/tesseract-ocr/tesseract")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️  Библиотека opencv-python не установлена. Оптимизация OCR недоступна.")
    print("   Установка: pip install opencv-python")

# Overall image processing availability
if IMAGE_PROCESSING_AVAILABLE and (QR_AVAILABLE or OCR_AVAILABLE):
    IMAGE_PROCESSING_AVAILABLE = True
else:
    IMAGE_PROCESSING_AVAILABLE = False
    print("Функции распознавания чеков будут недоступны")

# FNS API not used - scanning receipts directly


def decode_qr_from_image(image_bytes):
    """
    Декодирует QR-код из изображения

    Args:
        image_bytes: байты изображения

    Returns:
        str: строка с данными QR-кода

    Raises:
        ValueError: если QR-код не найден на изображении
        Exception: при других ошибках декодирования
    """
    if not IMAGE_PROCESSING_AVAILABLE or not QR_AVAILABLE:
        raise Exception("Библиотеки для распознавания QR-кодов не установлены (PIL, pyzbar)")

    try:
        # Открываем изображение из байтов
        image = Image.open(BytesIO(image_bytes))

        # Ищем QR-коды на изображении
        decoded_objects = pyzbar.decode(image)

        # Возвращаем данные первого найденного QR-кода
        if decoded_objects:
            qr_data = decoded_objects[0].data.decode('utf-8')
            print(f"QR-код успешно декодирован: {qr_data[:50]}...")
            return qr_data
        else:
            raise ValueError("QR-код не найден на изображении")

    except ValueError:
        raise  # Перебрасываем ValueError для отсутствия QR-кода
    except Exception as e:
        logger_config.logger.error(f"Ошибка при декодировании QR-кода: {e}")
        raise Exception(f"Ошибка при декодировании QR-кода: {e}")


def parse_receipt_from_qr(qr_data):
    """
    Парсит данные чека из QR-кода

    Args:
        qr_data: строка с данными QR-кода (формат: t=YYYYMMDDTHHMM&s=СУММА&fn=ФН&i=ФД&fp=ФП&n=ТИП)

    Returns:
        dict: структурированные данные чека (дата, сумма)
    """
    # Парсим QR-данные
    # Формат: t=YYYYMMDDTHHMM&s=СУММА&fn=ФН&i=ФД&fp=ФП&n=ТИП
    params = {}

    # Разбираем параметры из QR-кода
    for param in qr_data.split('&'):
        if '=' in param:
            key, value = param.split('=', 1)
            params[key] = value

    # Извлекаем необходимые параметры
    datetime_str = params.get('t', '')  # Дата и время (YYYYMMDDTHHMM)
    total_sum = params.get('s', '')     # Сумма

    print(f"Распознанные параметры из QR: Сумма={total_sum}, Время={datetime_str}")

    # Парсим дату
    try:
        receipt_date = datetime.strptime(datetime_str, '%Y%m%dT%H%M')
        date_formatted = receipt_date.strftime('%d.%m.%Y %H:%M')
    except:
        date_formatted = datetime.now().strftime('%d.%m.%Y %H:%M')

    return {
        'date': date_formatted,
        'shop': 'Неизвестно (QR)',
        'total': float(total_sum) if total_sum else 0,
        'items': [],
        'raw_params': params
    }


def ocr_fallback(image_bytes):
    """
    Запасной вариант: распознает текст чека через OCR

    Args:
        image_bytes: байты изображения

    Returns:
        dict: словарь с извлеченными данными (дата, магазин, сумма) или None при ошибке

    Raises:
        ValueError: если качество изображения слишком низкое для OCR
    """
    if not IMAGE_PROCESSING_AVAILABLE:
        raise Exception("Библиотеки для обработки изображений не установлены (PIL, pytesseract)")

    try:
        # Открываем изображение
        image = Image.open(BytesIO(image_bytes))

        # Проверяем качество изображения
        min_dimension = min(image.width, image.height)
        if min_dimension < 200:
            raise ValueError("Низкое качество изображения для OCR. Минимальный размер стороны должен быть не менее 200 пикселей.")

        # Предобработка изображения с помощью OpenCV
        if CV2_AVAILABLE:
            # Конвертируем PIL изображение в numpy array для OpenCV
            image_np = np.array(image)
            # Если изображение имеет альфа-канал, удаляем его
            if image_np.shape[-1] == 4:
                image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)
            # Конвертация в оттенки серого
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
            # Бинаризация (пороговая обработка)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # Удаление шума
            kernel = np.ones((1,1), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            # Увеличение контрастности
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            thresh = clahe.apply(thresh)
            # Конвертируем обратно в PIL изображение
            image = Image.fromarray(thresh)

        # Применяем OCR с русским языком
        text = pytesseract.image_to_string(image, lang='rus')
        print("OCR: текст успешно извлечен")
        print(f"Распознанный текст (первые 200 символов):\n{text[:200]}")

        # Инициализируем результат
        result = {
            'method': 'OCR',
            'shop': None,
            'date': None,
            'total': None,
            'raw_text': text
        }

        # Разбиваем текст на строки
        lines = text.split('\n')

        # Извлекаем название магазина (обычно в первых 3-5 строках)
        for i, line in enumerate(lines[:5]):
            line = line.strip()
            # Ищем строки с буквами (не только цифры)
            if line and len(line) > 3 and any(c.isalpha() for c in line):
                result['shop'] = line
                print(f"Найдено название магазина: {line}")
                break

        # Поиск даты (паттерн: DD.MM.YYYY или DD/MM/YYYY)
        date_pattern = r'(\d{2}[./]\d{2}[./]\d{4})'
        date_matches = re.findall(date_pattern, text)
        if date_matches:
            result['date'] = date_matches[0].replace('/', '.')
            print(f"Найдена дата: {result['date']}")

        # Поиск времени (паттерн: HH:MM)
        time_pattern = r'(\d{2}:\d{2})'
        time_matches = re.findall(time_pattern, text)
        if time_matches and result['date']:
            result['date'] = f"{result['date']} {time_matches[0]}"
            print(f"Найдено время: {time_matches[0]}")

        # Поиск общей суммы (паттерны: ИТОГ, СУММА, TOTAL, ВСЕГО)
        # Ищем паттерн: ключевое слово + число с копейками
        sum_pattern = r'(ИТОГ|СУММА|TOTAL|ВСЕГО|ИТОГО)[:\s]*(\d+[.,]\d{2})'
        sum_matches = re.findall(sum_pattern, text, re.IGNORECASE)

        if sum_matches:
            # Берем последнее совпадение (обычно итоговая сумма в конце чека)
            total_str = sum_matches[-1][1].replace(',', '.')
            result['total'] = float(total_str)
            print(f"Найдена сумма: {result['total']}")
        else:
            # Альтернативный поиск: просто ищем крупные суммы в тексте
            all_numbers = re.findall(r'\d+[.,]\d{2}', text)
            if all_numbers:
                # Берем максимальную сумму как итоговую
                numbers = [float(n.replace(',', '.')) for n in all_numbers]
                result['total'] = max(numbers)
                print(f"Найдена максимальная сумма: {result['total']}")

        # Проверяем, что хотя бы что-то удалось распознать
        if result['shop'] or result['date'] or result['total']:
            print("OCR: данные успешно извлечены")
            return result
        else:
            print("OCR: не удалось извлечь значимые данные")
            return None

    except Exception as e:
        logger_config.logger.error(f"OCR recognition error: {e}")
        return None





# Пример использования
if __name__ == "__main__":
    print("Модуль receipt_scanner загружен")
    print("Доступные функции:")
    print("1. decode_qr_from_image(image_bytes) - декодирование QR-кода")
    print("2. parse_receipt_from_qr(qr_data) - парсинг данных чека из QR")
    print("3. ocr_fallback(image_bytes) - OCR-распознавание")
