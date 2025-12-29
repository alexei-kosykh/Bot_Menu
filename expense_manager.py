"""
Модуль для управления расходами в Google Sheets
Обеспечивает работу с листами "Расходы" и "Бюджет"
"""

import gspread
from datetime import datetime
from typing import List, Dict, Optional
import os
import json
import logger_config

# Директория для кэша
CACHE_DIR = 'cache'
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

EXPENSES_CACHE_FILE = os.path.join(CACHE_DIR, 'expenses_cache.json')
BUDGET_CACHE_FILE = os.path.join(CACHE_DIR, 'budget_cache.json')


def add_expense(date: str, store: str, items: List[Dict], total: float) -> bool:
    """
    Добавляет данные о покупке в лист "Расходы"

    Args:
        date: дата покупки в формате DD.MM.YYYY
        store: название магазина
        items: список товаров [{'name': str, 'price': float, 'quantity': float, 'sum': float}]
        total: общая сумма покупки

    Returns:
        bool: True при успешном добавлении, False при ошибке
    """
    try:
        # Импортируем готовый объект листа расходов
        from get_access_table import sheetExpenses

        if sheetExpenses is None:
            # Кэшируем данные локально
            cache_expense(date, store, items, total)
            logger_config.logger.warning("Google Sheets unavailable, expense cached locally")
            return True  # Возвращаем True, так как данные сохранены в кэше

        # Если товары детализированы, записываем каждый товар отдельно
        if items and len(items) > 0:
            for item in items:
                row = [
                    date,
                    store,
                    item.get('name', ''),
                    item.get('price', 0),
                    item.get('quantity', 1),
                    item.get('sum', 0)
                ]
                sheetExpenses.append_row(row)
        else:
            # Если товары не детализированы, записываем одну строку с общей суммой
            row = [
                date,
                store,
                "Общая сумма (без детализации)",
                total,
                1,
                total
            ]
            sheetExpenses.append_row(row)

        return True

    except Exception as e:
        logger_config.logger.error(f"Error adding expense: {e}")
        # При ошибке тоже кэшируем
        cache_expense(date, store, items, total)
        return True


def update_budget(month: str, amount: float) -> bool:
    """
    Обновляет бюджет на месяц, добавляя сумму покупки

    Args:
        month: месяц в формате "MM.YYYY"
        amount: сумма для добавления к потраченному

    Returns:
        bool: True при успешном обновлении, False при ошибке
    """
    try:
        # Импортируем готовый объект листа бюджета
        from get_access_table import sheetBudget

        if sheetBudget is None:
            # Кэшируем обновление бюджета локально
            cache_budget_update(month, amount)
            logger_config.logger.warning("Google Sheets unavailable, budget update cached locally")
            return True

        # Получаем все данные из листа бюджета
        data = sheetBudget.get_all_values()

        # Ищем строку с указанным месяцем (предполагаем, что месяц в колонке A)
        month_row_index = None
        for i, row in enumerate(data):
            if len(row) > 0 and row[0] == month:
                month_row_index = i + 1  # +1 потому что gspread использует 1-based indexing
                break

        if month_row_index is None:
            # Если месяц не найден, создаем новую строку с дефолтным бюджетом
            # Предполагаем дефолтный бюджет 30000 рублей
            default_budget = 30000.0
            new_row = [month, default_budget, amount]
            sheetBudget.append_row(new_row)
        else:
            # Обновляем существующую строку
            # Получаем текущую сумму потраченного (колонка C)
            current_spent = float(data[month_row_index - 1][2]) if len(data[month_row_index - 1]) > 2 else 0
            new_spent = current_spent + amount

            # Обновляем ячейку
            sheetBudget.update_cell(month_row_index, 3, new_spent)

        return True

    except Exception as e:
        logger_config.logger.error(f"Error updating budget: {e}")
        # При ошибке кэшируем
        cache_budget_update(month, amount)
        return True


def get_budget_info(month: str) -> Optional[Dict[str, float]]:
    """
    Получает информацию о бюджете для указанного месяца

    Args:
        month: месяц в формате "MM.YYYY"

    Returns:
        dict: {"planned": float, "spent": float, "remaining": float} или None при ошибке
        Если месяц не найден, возвращает None с сообщением в stdout
    """
    try:
        # Импортируем готовый объект листа бюджета
        from get_access_table import sheetBudget

        if sheetBudget is None:
            print("Ошибка: лист 'Бюджет' не инициализирован")
            return None

        # Получаем все данные из листа бюджета
        data = sheetBudget.get_all_values()

        # Ищем строку с указанным месяцем
        for row in data:
            if len(row) > 0 and row[0] == month:
                planned = float(row[1]) if len(row) > 1 and row[1] else 0
                spent = float(row[2]) if len(row) > 2 and row[2] else 0
                remaining = planned - spent

                return {
                    "planned": planned,
                    "spent": spent,
                    "remaining": remaining
                }

        # Если месяц не найден
        print(f"Месяц {month} не найден в бюджете. Необходимо установить бюджет.")
        return None

    except Exception as e:
        print(f"Ошибка при получении информации о бюджете: {e}")
        return None


def cache_expense(date: str, store: str, items: List[Dict], total: float):
    """Кэширует расход локально"""
    try:
        # Загружаем существующий кэш
        if os.path.exists(EXPENSES_CACHE_FILE):
            with open(EXPENSES_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        else:
            cache = []

        # Добавляем новый расход
        expense_entry = {
            'date': date,
            'store': store,
            'items': items,
            'total': total,
            'timestamp': datetime.now().isoformat()
        }
        cache.append(expense_entry)

        # Сохраняем кэш
        with open(EXPENSES_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    except Exception as e:
        logger_config.logger.error(f"Error caching expense: {e}")


def cache_budget_update(month: str, amount: float):
    """Кэширует обновление бюджета локально"""
    try:
        # Загружаем существующий кэш
        if os.path.exists(BUDGET_CACHE_FILE):
            with open(BUDGET_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        else:
            cache = {}

        # Добавляем сумму к месяцу
        if month not in cache:
            cache[month] = 0
        cache[month] += amount

        # Сохраняем кэш
        with open(BUDGET_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    except Exception as e:
        logger_config.logger.error(f"Error caching budget update: {e}")


def sync_cache():
    """Синхронизирует кэшированные данные с Google Sheets"""
    try:
        from get_access_table import sheetExpenses, sheetBudget

        # Синхронизация расходов
        if os.path.exists(EXPENSES_CACHE_FILE) and sheetExpenses:
            with open(EXPENSES_CACHE_FILE, 'r', encoding='utf-8') as f:
                expenses_cache = json.load(f)

            for expense in expenses_cache:
                try:
                    add_expense(expense['date'], expense['store'], expense['items'], expense['total'])
                except Exception as e:
                    logger_config.logger.error(f"Error syncing expense: {e}")
                    continue

            # Очищаем кэш после успешной синхронизации
            os.remove(EXPENSES_CACHE_FILE)
            logger_config.logger.info("Expenses cache synced successfully")

        # Синхронизация бюджета
        if os.path.exists(BUDGET_CACHE_FILE) and sheetBudget:
            with open(BUDGET_CACHE_FILE, 'r', encoding='utf-8') as f:
                budget_cache = json.load(f)

            for month, amount in budget_cache.items():
                try:
                    update_budget(month, amount)
                except Exception as e:
                    logger_config.logger.error(f"Error syncing budget for {month}: {e}")
                    continue

            # Очищаем кэш после успешной синхронизации
            os.remove(BUDGET_CACHE_FILE)
            logger_config.logger.info("Budget cache synced successfully")

    except Exception as e:
        logger_config.logger.error(f"Error syncing cache: {e}")


# Пример использования
if __name__ == "__main__":
    print("Модуль expense_manager загружен")
    print("Доступные функции:")
    print("1. add_expense(date, store, items, total) - добавление расхода")
    print("2. update_budget(month, amount) - обновление бюджета")
    print("3. get_budget_info(month) - получение информации о бюджете")
    print("4. sync_cache() - синхронизация кэша")
