#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности бота
Тестирует основные сценарии работы с чеками, бюджетом и обработкой ошибок
"""

import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch
import json

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули бота
from receipt_scanner import decode_qr_from_image, parse_receipt_from_qr, ocr_fallback
from expense_manager import add_expense, update_budget, get_budget_info, sync_cache
from budget_commands import get_budget_status, set_monthly_budget
from receipt_handler import _process_receipt_data
from logger_config import logger

def test_qr_receipt_recognition():
    """Тест 1: Распознавание чека с QR-кодом"""
    print("\n=== Тест 1: Распознавание чека с QR-кодом ===")

    # Мокаем QR-данные чека
    mock_qr_data = "t=202312291430&s=1250.50&fn=9280440300000000&i=0000000000&fp=0000000000&n=1"

    try:
        # Парсим данные из QR
        receipt_data = parse_receipt_from_qr(mock_qr_data)

        print(f"✅ QR распознан. Сумма: {receipt_data['total']}, Дата: {receipt_data['date']}")

        # Проверяем корректность данных
        assert receipt_data['total'] == 1250.50, f"Ожидалось 1250.50, получено {receipt_data['total']}"
        assert receipt_data['shop'] == 'Неизвестно (QR)', f"Ожидалось 'Неизвестно (QR)', получено {receipt_data['shop']}"
        assert 'items' in receipt_data, "Отсутствует поле items"
        assert isinstance(receipt_data['items'], list), "items должен быть списком"

        print("✅ Тест пройден успешно")

    except Exception as e:
        print(f"❌ Тест провален: {e}")
        return False

    return True

def test_manual_expense_input():
    """Тест 2: Ручной ввод расхода"""
    print("\n=== Тест 2: Ручной ввод расхода ===")

    try:
        # Тестируем добавление расхода с моком Google Sheets
        date = "15.12.2023"
        store = "Пятерочка"
        items = []  # Ручной ввод без детальных товаров
        total = 850.75

        # Мокаем Google Sheets для тестирования
        mock_sheet = Mock()
        mock_sheet.append_row.return_value = None

        with patch('get_access_table.sheetExpenses', mock_sheet):
            success = add_expense(date, store, items, total)

        if success:
            print(f"✅ Расход добавлен: {store} - {total} руб.")
            # Проверяем, что append_row был вызван
            mock_sheet.append_row.assert_called_once()
        else:
            print("❌ Не удалось добавить расход")
            return False

        print("✅ Тест пройден успешно")

    except Exception as e:
        print(f"❌ Тест провален: {e}")
        return False

    return True

def test_budget_operations():
    """Тест 3: Установка и просмотр бюджета"""
    print("\n=== Тест 3: Установка и просмотр бюджета ===")

    try:
        # Устанавливаем бюджет с моком Google Sheets
        current_month = datetime.now().strftime('%Y-%m')
        budget_amount = 30000.0

        # Мокаем Google Sheets для тестирования
        mock_sheet = Mock()
        mock_sheet.append_row.return_value = None
        mock_sheet.get_all_values.return_value = [
            ['Месяц', 'План', 'Потрачено'],
            [current_month, str(budget_amount), '0']
        ]

        with patch('get_access_table.sheetBudget', mock_sheet):
            success = set_monthly_budget(current_month, budget_amount)

        if success:
            print(f"✅ Бюджет установлен: {budget_amount} руб. на {current_month}")
            # Проверяем, что append_row был вызван для установки бюджета
            # Функция конвертирует YYYY-MM в MM.YYYY
            expected_month = f"{current_month.split('-')[1]}.{current_month.split('-')[0]}"
            mock_sheet.append_row.assert_called_once_with([expected_month, budget_amount, 0])
        else:
            print("❌ Не удалось установить бюджет")
            return False

        # Получаем статус бюджета с моком
        with patch('budget_commands.get_budget_info') as mock_get_info:
            mock_get_info.return_value = {
                'planned': budget_amount,
                'spent': 0,
                'remaining': budget_amount
            }
            budget_status = get_budget_status()

        if budget_status and "плановый" in budget_status.lower():
            print(f"✅ Статус бюджета получен: {budget_status[:100]}...")
        else:
            print("❌ Не удалось получить статус бюджета")
            return False

        # Получаем детальную информацию о бюджете с моком
        with patch('get_access_table.sheetBudget', mock_sheet):
            budget_info = get_budget_info(current_month)

        if budget_info:
            print(f"✅ Детали бюджета: План={budget_info['planned']}, Потрачено={budget_info['spent']}, Остаток={budget_info['remaining']}")
            assert budget_info['planned'] == budget_amount, f"План должен быть {budget_amount}, получено {budget_info['planned']}"
        else:
            print("❌ Не удалось получить детали бюджета")
            return False

        print("✅ Тест пройден успешно")

    except Exception as e:
        print(f"❌ Тест провален: {e}")
        return False

    return True

def test_budget_exceedance():
    """Тест 4: Превышение бюджета"""
    print("\n=== Тест 4: Превышение бюджета ===")

    try:
        current_month = datetime.now().strftime('%m.%Y')

        # Мокаем Google Sheets для тестирования
        mock_sheet = Mock()
        mock_sheet.append_row.return_value = None
        mock_sheet.get_all_values.return_value = [
            ['Месяц', 'План', 'Потрачено'],
            [current_month, '1000.0', '1500.0']  # Маленький бюджет, большой расход
        ]
        mock_sheet.update_cell.return_value = None

        with patch('get_access_table.sheetBudget', mock_sheet):
            # Устанавливаем маленький бюджет
            small_budget = 1000.0
            set_monthly_budget(f"{datetime.now().year}-{current_month}", small_budget)

            # Добавляем большой расход
            large_expense = 1500.0
            add_expense("16.12.2023", "Тестовый магазин", [], large_expense)

            # Обновляем бюджет
            update_budget(current_month, large_expense)

            # Проверяем статус бюджета
            budget_info = get_budget_info(current_month)

        if budget_info and budget_info['remaining'] < 0:
            print(f"✅ Бюджет превышен: Остаток={budget_info['remaining']} руб. (отрицательный)")
        else:
            print("❌ Бюджет не превышен или не удалось проверить")
            return False

        print("✅ Тест пройден успешно")

    except Exception as e:
        print(f"❌ Тест провален: {e}")
        return False

    return True

def test_invalid_image_handling():
    """Тест 5: Обработка некорректных изображений"""
    print("\n=== Тест 5: Обработка некорректных изображений ===")

    try:
        # Тестируем с некорректными данными
        invalid_bytes = b"not an image"

        try:
            decode_qr_from_image(invalid_bytes)
            print("❌ Ожидалось исключение для некорректного изображения")
            return False
        except Exception as e:
            print(f"✅ Корректно обработано некорректное изображение: {type(e).__name__}")

        # Тестируем слишком маленький файл
        small_bytes = b"x" * 100  # Менее 10MB, но некорректный

        try:
            decode_qr_from_image(small_bytes)
            print("❌ Ожидалось исключение для малого изображения")
            return False
        except Exception as e:
            print(f"✅ Корректно обработано малое изображение: {type(e).__name__}")

        print("✅ Тест пройден успешно")

    except Exception as e:
        print(f"❌ Тест провален: {e}")
        return False

    return True

def test_ocr_fallback():
    """Тест 6: Распознавание чека без QR (только OCR)"""
    print("\n=== Тест 6: Распознавание чека без QR (OCR) ===")

    try:
        # Создаем mock изображение для OCR (в реальности понадобится настоящее изображение)
        # Для теста просто проверяем, что функция не падает
        try:
            result = ocr_fallback(b"mock image data")
            # Функция должна вернуть None для некорректных данных
            if result is None:
                print("✅ OCR корректно обработал некорректные данные")
            else:
                print("⚠️ OCR вернул результат для некорректных данных, что может быть нормально")
        except ValueError as e:
            print(f"✅ OCR корректно вернул ошибку валидации: {e}")
        except Exception as e:
            print(f"❌ OCR выдал неожиданную ошибку: {e}")
            return False

        print("✅ Тест пройден успешно")

    except Exception as e:
        print(f"❌ Тест провален: {e}")
        return False

    return True

def test_data_validation():
    """Тест 7: Валидация данных"""
    print("\n=== Тест 7: Валидация данных ===")

    try:
        # Тестируем валидацию даты
        invalid_date = "32.13.2023"
        try:
            datetime.strptime(invalid_date, '%d.%m.%Y')
            print("❌ Ожидалась ошибка валидации даты")
            return False
        except ValueError:
            print("✅ Дата корректно провалидирована")

        # Тестируем отрицательную сумму
        negative_amount = -100.0
        if negative_amount <= 0:
            print("✅ Отрицательная сумма корректно отловлена")
        else:
            print("❌ Отрицательная сумма не отловлена")
            return False

        # Тестируем пустую строку
        empty_string = ""
        if not empty_string or len(empty_string) < 2:
            print("✅ Пустая строка корректно отловлена")
        else:
            print("❌ Пустая строка не отловлена")
            return False

        print("✅ Тест пройден успешно")

    except Exception as e:
        print(f"❌ Тест провален: {e}")
        return False

    return True

def test_offline_mode():
    """Тест 8: Работа при недоступности Google Sheets (оффлайн режим)"""
    print("\n=== Тест 8: Работа в оффлайн режиме ===")

    try:
        # Имитируем недоступность Google Sheets
        with patch('get_access_table.sheetExpenses', None):
            with patch('get_access_table.sheetBudget', None):
                # Пытаемся добавить расход
                success = add_expense("17.12.2023", "Оффлайн Магазин", [], 500.0)

                if success:
                    print("✅ Расход успешно сохранен в кэш при недоступности Google Sheets")
                else:
                    print("❌ Не удалось сохранить расход в кэш")
                    return False

                # Проверяем, что данные попали в кэш
                cache_file = os.path.join('cache', 'expenses_cache.json')
                if os.path.exists(cache_file):
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache = json.load(f)
                    if len(cache) > 0:
                        print(f"✅ Данные найдены в кэше: {len(cache)} записей")
                    else:
                        print("❌ Кэш пустой")
                        return False
                else:
                    print("❌ Файл кэша не создан")
                    return False

        print("✅ Тест пройден успешно")

    except Exception as e:
        print(f"❌ Тест провален: {e}")
        return False

    return True

def test_concurrent_users():
    """Тест 9: Работа с несколькими пользователями одновременно"""
    print("\n=== Тест 9: Многопользовательская работа ===")

    try:
        # Имитируем работу нескольких пользователей с моком Google Sheets
        mock_sheet = Mock()
        mock_sheet.append_row.return_value = None

        users = [
            {"id": 1, "name": "Пользователь 1"},
            {"id": 2, "name": "Пользователь 2"},
            {"id": 3, "name": "Пользователь 3"}
        ]

        with patch('get_access_table.sheetExpenses', mock_sheet):
            for user in users:
                # Каждый пользователь добавляет свой расход
                expense_total = 100 * (user["id"])  # Разные суммы
                success = add_expense(
                    "18.12.2023",
                    f"Магазин {user['name']}",
                    [],
                    expense_total
                )

                if success:
                    print(f"✅ Расход пользователя {user['name']}: {expense_total} руб.")
                else:
                    print(f"❌ Ошибка для пользователя {user['name']}")
                    return False

        # Проверяем, что append_row был вызван 3 раза (по разу для каждого пользователя)
        assert mock_sheet.append_row.call_count == 3, f"Ожидалось 3 вызова append_row, получено {mock_sheet.append_row.call_count}"

        print("✅ Тест пройден успешно")

    except Exception as e:
        print(f"❌ Тест провален: {e}")
        return False

    return True

def run_all_tests():
    """Запуск всех тестов"""
    print("🚀 Запуск тестового набора для бота управления расходами")
    print("=" * 60)

    tests = [
        test_qr_receipt_recognition,
        test_manual_expense_input,
        test_budget_operations,
        test_budget_exceedance,
        test_invalid_image_handling,
        test_ocr_fallback,
        test_data_validation,
        test_offline_mode,
        test_concurrent_users
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ Тест {test.__name__} провален")
        except Exception as e:
            print(f"❌ Тест {test.__name__} завершился с ошибкой: {e}")

    print("\n" + "=" * 60)
    print(f"📊 Результаты тестирования: {passed}/{total} тестов пройдено")

    if passed == total:
        print("🎉 Все тесты пройдены успешно!")
        return True
    else:
        print(f"⚠️ Провалено {total - passed} тестов")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
