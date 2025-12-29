"""
Модуль команд для работы с бюджетом
Обеспечивает пользовательские команды для установки и просмотра бюджета
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any
from expense_manager import update_budget, get_budget_info


def set_monthly_budget(month: str, amount: float) -> bool:
    """
    Устанавливает плановый бюджет на месяц

    Args:
        month: месяц в формате YYYY-MM (например, "2024-12")
        amount: сумма бюджета

    Returns:
        bool: True при успешной установке, False при ошибке
    """
    try:
        # Проверяем корректность формата месяца
        if not re.match(r'^\d{4}-\d{2}$', month):
            print(f"Ошибка: некорректный формат месяца '{month}'. Используйте формат YYYY-MM (например, 2024-12)")
            return False

        # Проверяем, что месяц в допустимом диапазоне
        year, month_num = map(int, month.split('-'))
        if not (1 <= month_num <= 12):
            print(f"Ошибка: недопустимый номер месяца {month_num}. Должен быть от 01 до 12")
            return False

        # Проверяем, что сумма положительная
        if amount <= 0:
            print(f"Ошибка: сумма бюджета должна быть положительной, получено: {amount}")
            return False

        # Конвертируем формат для хранения в таблице (MM.YYYY)
        sheet_month = f"{month_num:02d}.{year}"

        # Получаем доступ к листу бюджета
        from get_access_table import sheetBudget

        if sheetBudget is None:
            print("Ошибка: лист 'Бюджет' не инициализирован")
            return False

        # Получаем все данные из листа бюджета
        data = sheetBudget.get_all_values()

        # Ищем строку с указанным месяцем (используем конвертированный формат)
        month_row_index = None
        for i, row in enumerate(data):
            if len(row) > 0 and row[0] == sheet_month:
                month_row_index = i + 1  # +1 потому что gspread использует 1-based indexing
                break

        if month_row_index is None:
            # Если месяц не найден, создаем новую строку
            new_row = [sheet_month, amount, 0]  # месяц, плановый бюджет, потрачено (0)
            sheetBudget.append_row(new_row)
            print(f"Бюджет на {month} установлен: {amount} руб.")
        else:
            # Обновляем существующую строку (колонка B - плановый бюджет)
            # Сохраняем текущую сумму потраченного (колонка C)
            current_spent = float(data[month_row_index - 1][2]) if len(data[month_row_index - 1]) > 2 else 0
            sheetBudget.update_cell(month_row_index, 2, amount)  # Обновляем плановый бюджет
            print(f"Бюджет на {month} обновлен: {amount} руб. (потрачено: {current_spent} руб.)")

        return True

    except Exception as e:
        print(f"Ошибка при установке бюджета: {e}")
        return False


def get_budget_status(month: Optional[str] = None) -> Optional[str]:
    """
    Получает статус бюджета на указанный месяц

    Args:
        month: месяц в формате MM.YYYY (например, "12.2024") или YYYY-MM (например, "2024-12"), или None для текущего месяца

    Returns:
        str: отформатированный статус бюджета с эмодзи или None при ошибке
    """
    try:
        # Если месяц не указан, используем текущий
        if month is None:
            now = datetime.now()
            month = f"{now.month:02d}.{now.year}"

        # Преобразуем формат из MM.YYYY в MM.YYYY для get_budget_info
        # Функция get_budget_info ожидает формат MM.YYYY, но если передан YYYY-MM, конвертируем
        budget_month = month
        if re.match(r'^\d{4}-\d{2}$', month):
            # Конвертируем YYYY-MM в MM.YYYY
            year, month_num = month.split('-')
            budget_month = f"{month_num}.{year}"

        budget_info = get_budget_info(budget_month)

        if budget_info is None:
            return f"❌ Бюджет на {month} не найден. Установите бюджет командой set_monthly_budget."

        planned = budget_info["planned"]
        spent = budget_info["spent"]
        remaining = budget_info["remaining"]

        # Вычисляем процент использования бюджета
        if planned > 0:
            usage_percent = (spent / planned) * 100
        else:
            usage_percent = 0

        # Определяем статус и эмодзи
        if usage_percent >= 100:
            status_emoji = "🚨"
            status_text = "ПРЕВЫШЕН"
        elif usage_percent >= 80:
            status_emoji = "⚠️"
            status_text = "КРИТИЧЕСКИЙ"
        elif usage_percent >= 60:
            status_emoji = "🟡"
            status_text = "ВЫСОКИЙ"
        else:
            status_emoji = "🟢"
            status_text = "НОРМАЛЬНЫЙ"

        # Форматируем ответ
        response = f"""
{status_emoji} **Бюджет на {month}**

💰 Плановый: {planned:,.0f} руб.
💸 Потрачено: {spent:,.0f} руб.
📊 Остаток: {remaining:,.0f} руб.
📈 Использовано: {usage_percent:.1f}%

**Статус: {status_text}**
"""

        return response.strip()

    except Exception as e:
        print(f"Ошибка при получении статуса бюджета: {e}")
        return None


def get_budget_notifications(month: Optional[str] = None) -> Optional[str]:
    """
    Получает уведомления о бюджете (для показа после покупки)

    Args:
        month: месяц в формате MM.YYYY или YYYY-MM, или None для текущего месяца

    Returns:
        str: уведомление о бюджете или None если уведомление не требуется
    """
    try:
        # Если месяц не указан, используем текущий
        if month is None:
            now = datetime.now()
            month = f"{now.month:02d}.{now.year}"

        # Преобразуем формат
        budget_month = month
        if re.match(r'^\d{4}-\d{2}$', month):
            year, month_num = month.split('-')
            budget_month = f"{month_num}.{year}"

        budget_info = get_budget_info(budget_month)

        if budget_info is None:
            return None

        planned = budget_info["planned"]
        spent = budget_info["spent"]

        # Вычисляем процент использования бюджета
        if planned > 0:
            usage_percent = (spent / planned) * 100
        else:
            return None

        # Формируем уведомления
        notifications = []

        if usage_percent >= 100:
            notifications.append(f"🚨 **КРИТИЧЕСКОЕ УВЕДОМЛЕНИЕ**\nБюджет превышен на {(usage_percent - 100):.1f}%!")
        elif usage_percent >= 80:
            remaining_percent = 100 - usage_percent
            notifications.append(f"⚠️ **ПРЕДУПРЕЖДЕНИЕ**\nБюджет использован на {usage_percent:.1f}%. Осталось {remaining_percent:.1f}%.")

        if notifications:
            notifications.append(f"💰 Плановый: {planned:,.0f} ₽ | Потрачено: {spent:,.0f} ₽")
            return "\n\n".join(notifications)

        return None

    except Exception as e:
        print(f"Ошибка при получении уведомлений бюджета: {e}")
        return None


# Пример использования
if __name__ == "__main__":
    print("Модуль budget_commands загружен")
    print("Доступные функции:")
    print("1. set_monthly_budget(month, amount) - установка бюджета")
    print("2. get_budget_status(month=None) - получение статуса бюджета")
