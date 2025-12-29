"""
Обработчики для работы с бюджетом и историей расходов
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from collections import defaultdict
from telegram import Update
from telegram.ext import ContextTypes

from budget_commands import get_budget_status, set_monthly_budget
from get_access_table import sheetExpenses


async def handle_budget_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает запрос статуса бюджета

    Args:
        update: объект обновления Telegram
        context: контекст бота
    """
    try:
        # Определяем, откуда пришел запрос (сообщение или callback)
        chat = None
        if update.message:
            chat = update.message
        elif update.callback_query:
            chat = update.callback_query.message

        if not chat:
            return

        # Получаем статус бюджета для текущего месяца
        budget_info = get_budget_status()

        if budget_info:
            await chat.reply_text(budget_info)
        else:
            await chat.reply_text("❌ Не удалось получить статус бюджета. Проверьте настройки.")

    except Exception as e:
        if update.message:
            await update.message.reply_text(f"❌ Ошибка при получении статуса бюджета: {e}")
        elif update.callback_query:
            await update.callback_query.message.reply_text(f"❌ Ошибка при получении статуса бюджета: {e}")


async def handle_set_budget(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """
    Обрабатывает установку бюджета

    Args:
        update: объект обновления Telegram
        context: контекст бота
        text: текст с суммой бюджета
    """
    try:
        # Парсим сумму из текста
        amount_str = text.strip()

        # Убираем возможные лишние символы (руб, ₽, etc.)
        amount_str = re.sub(r'[^\d.,]', '', amount_str)

        # Конвертируем в число
        try:
            amount = float(amount_str.replace(',', '.'))
            if amount <= 0:
                await update.message.reply_text("❌ Сумма бюджета должна быть положительным числом.")
                return
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите корректную сумму (например: 25000 или 25000.50).")
            return

        # Получаем текущий месяц в формате YYYY-MM
        current_month = datetime.now().strftime('%Y-%m')

        # Устанавливаем бюджет
        success = set_monthly_budget(current_month, amount)

        if success:
            # Получаем обновленный статус бюджета
            budget_status = get_budget_status()

            response = f"""
✅ **Бюджет установлен!**

📅 Месяц: {current_month}
💰 Сумма: {amount:,.0f} ₽
"""

            if budget_status:
                response += f"\n{budget_status}"

            await update.message.reply_text(response)
        else:
            await update.message.reply_text("❌ Ошибка при установке бюджета. Попробуйте позже.")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при установке бюджета: {e}")


async def handle_expense_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает запрос статистики расходов

    Args:
        update: объект обновления Telegram
        context: контекст бота
    """
    try:
        # Определяем, откуда пришел запрос (сообщение или callback)
        chat = None
        if update.message:
            chat = update.message
        elif update.callback_query:
            chat = update.callback_query.message

        if not chat:
            return

        await chat.reply_text("📊 Собираю статистику расходов...")

        # Получаем данные из листа расходов
        if sheetExpenses is None:
            await chat.reply_text("❌ Ошибка: лист 'Расходы' не инициализирован.")
            return

        expense_data = sheetExpenses.get_all_values()

        if not expense_data or len(expense_data) <= 1:  # Пустой лист или только заголовки
            await chat.reply_text("📭 Нет данных о расходах для анализа.")
            return

        # Определяем текущий и предыдущий месяцы
        now = datetime.now()
        current_month = f"{now.month:02d}.{now.year}"
        prev_month = f"{(now.month - 1):02d}.{now.year}" if now.month > 1 else f"12.{now.year - 1}"

        # Анализируем расходы
        current_expenses = []
        prev_expenses = []
        total_current = 0
        total_prev = 0

        for row in expense_data[1:]:  # Пропускаем заголовок
            if len(row) < 6:  # Недостаточно колонок
                continue

            try:
                expense_date = row[0]  # Дата
                store = row[1]  # Магазин
                item_price = float(row[3]) if row[3] else 0  # Цена
                quantity = float(row[4]) if row[4] else 1  # Количество
                item_total = float(row[5]) if row[5] else 0  # Сумма

                # Определяем месяц расхода
                expense_month = _get_month_from_date(expense_date)

                if expense_month == current_month:
                    current_expenses.append({
                        'date': expense_date,
                        'store': store,
                        'total': item_total
                    })
                    total_current += item_total
                elif expense_month == prev_month:
                    prev_expenses.append({
                        'date': expense_date,
                        'store': store,
                        'total': item_total
                    })
                    total_prev += item_total

            except (ValueError, IndexError):
                continue

        # Группируем по категориям для текущего месяца
        category_totals = defaultdict(float)
        daily_totals = defaultdict(float)

        for expense in current_expenses:
            # Определяем категорию
            category = _extract_category_from_store(expense['store'])
            category_totals[category] += expense['total']

            # Группируем по дням
            day = expense['date'].split('.')[0] if '.' in expense['date'] else expense['date'][:2]
            daily_totals[day] += expense['total']

        # Формируем отчет
        report = f"""
📊 **Статистика расходов за {now.month:02d}.{now.year}**

💰 **Общая сумма:** {total_current:,.0f} ₽ ({len(current_expenses)} покупок)
"""

        # Топ-5 категорий
        if category_totals:
            report += "\n🏷 **Топ-5 категорий:**\n"
            sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]

            for i, (category, amount) in enumerate(sorted_categories, 1):
                percentage = (amount / total_current * 100) if total_current > 0 else 0
                report += f"{i}. {category}: {amount:,.0f} ₽ ({percentage:.1f}%)\n"
        else:
            report += "\n🏷 Нет данных по категориям\n"

        # График расходов по дням (текстовый)
        if daily_totals:
            report += "\n📈 **Расходы по дням:**\n"
            max_amount = max(daily_totals.values()) if daily_totals else 0
            chart_width = 20

            sorted_days = sorted(daily_totals.items(), key=lambda x: int(x[0]))

            for day, amount in sorted_days:
                if max_amount > 0:
                    bar_length = int((amount / max_amount) * chart_width)
                    bar = '█' * bar_length
                else:
                    bar = ''
                report += f"{day:2d}: {bar} {amount:,.0f} ₽\n"
        else:
            report += "\n📈 Нет данных по дням\n"

        # Сравнение с предыдущим месяцем
        if total_prev > 0:
            diff = total_current - total_prev
            diff_percent = (diff / total_prev * 100) if total_prev > 0 else 0

            if diff > 0:
                comparison = f"📈 Больше на {diff:,.0f} ₽ (+{diff_percent:.1f}%)"
            elif diff < 0:
                comparison = f"📉 Меньше на {abs(diff):,.0f} ₽ ({diff_percent:.1f}%)"
            else:
                comparison = "➡️ Без изменений"
        else:
            comparison = "📊 Предыдущий месяц: данных нет"

        report += f"\n🔄 **Сравнение с предыдущим месяцем:**\n{comparison}"

        await chat.reply_text(report)

    except Exception as e:
        await chat.reply_text(f"❌ Ошибка при получении статистики: {e}")


def _get_month_from_date(expense_date: str) -> str:
    """
    Извлекает месяц из даты в формате DD.MM.YYYY

    Args:
        expense_date: дата в формате DD.MM.YYYY

    Returns:
        str: месяц в формате MM.YYYY
    """
    try:
        if '.' in expense_date:
            parts = expense_date.split('.')
            if len(parts) >= 3:
                day, month, year = parts[0], parts[1], parts[2]
                return f"{month}.{year}"
    except (ValueError, IndexError):
        pass
    return ""


async def handle_expense_history(update: Update, context: ContextTypes.DEFAULT_TYPE, month: Optional[str] = None) -> None:
    """
    Обрабатывает запрос истории расходов

    Args:
        update: объект обновления Telegram
        context: контекст бота
        month: месяц в формате MM.YYYY (опционально)
    """
    try:
        # Определяем, откуда пришел запрос (сообщение или callback)
        chat = None
        if update.message:
            chat = update.message
        elif update.callback_query:
            chat = update.callback_query.message

        if not chat:
            return

        await chat.reply_text("📊 Собираю данные о расходах...")

        # Определяем месяц для фильтрации
        if month is None:
            # Используем текущий месяц
            now = datetime.now()
            target_month = f"{now.month:02d}.{now.year}"
            month_name = f"{now.month:02d}.{now.year}"
        else:
            target_month = month
            month_name = month

        # Получаем данные из листа расходов
        if sheetExpenses is None:
            await chat.reply_text("❌ Ошибка: лист 'Расходы' не инициализирован.")
            return

        expense_data = sheetExpenses.get_all_values()

        if not expense_data or len(expense_data) <= 1:  # Пустой лист или только заголовки
            await chat.reply_text(f"📭 За {month_name} расходов не найдено.")
            return

        # Фильтруем и анализируем расходы
        expenses = []
        total_spent = 0

        for row in expense_data[1:]:  # Пропускаем заголовок
            if len(row) < 6:  # Недостаточно колонок
                continue

            try:
                expense_date = row[0]  # Дата
                store = row[1]  # Магазин
                item_name = row[2]  # Название товара
                item_price = float(row[3]) if row[3] else 0  # Цена
                quantity = float(row[4]) if row[4] else 1  # Количество
                item_total = float(row[5]) if row[5] else 0  # Сумма

                # Проверяем, относится ли расход к целевому месяцу
                if target_month and not _is_expense_in_month(expense_date, target_month):
                    continue

                expenses.append({
                    'date': expense_date,
                    'store': store,
                    'item': item_name,
                    'price': item_price,
                    'quantity': quantity,
                    'total': item_total
                })

                total_spent += item_total

            except (ValueError, IndexError):
                continue  # Пропускаем некорректные строки

        if not expenses:
            await chat.reply_text(f"📭 За {month_name} расходов не найдено.")
            return

        # Группируем по категориям/магазинам
        category_totals = defaultdict(float)
        store_totals = defaultdict(float)

        for expense in expenses:
            # Определяем категорию из названия магазина (если есть в скобках)
            store_name = expense['store']
            category = _extract_category_from_store(store_name)

            category_totals[category] += expense['total']
            store_totals[store_name] += expense['total']

        # Формируем отчет
        report = f"""
📊 **История расходов за {month_name}**

💰 **Общая сумма:** {total_spent:,.0f} ₽
🛒 **Количество покупок:** {len(expenses)} товаров

📂 **По категориям:**
"""

        # Сортируем категории по сумме (убывание)
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)

        for category, amount in sorted_categories:
            percentage = (amount / total_spent * 100) if total_spent > 0 else 0
            report += f"• {category}: {amount:,.0f} ₽ ({percentage:.1f}%)\n"

        report += "\n🏪 **По магазинам:**\n"

        # Сортируем магазины по сумме (убывание)
        sorted_stores = sorted(store_totals.items(), key=lambda x: x[1], reverse=True)

        for store, amount in sorted_stores[:10]:  # Показываем топ-10 магазинов
            percentage = (amount / total_spent * 100) if total_spent > 0 else 0
            report += f"• {store}: {amount:,.0f} ₽ ({percentage:.1f}%)\n"

        if len(sorted_stores) > 10:
            report += f"... и ещё {len(sorted_stores) - 10} магазинов\n"

        # Добавляем последние 5 покупок
        report += "\n🕐 **Последние покупки:**\n"
        recent_expenses = sorted(expenses, key=lambda x: x['date'], reverse=True)[:5]

        for expense in recent_expenses:
            report += f"• {expense['date']}: {expense['store']} - {expense['total']:,.0f} ₽\n"

        await chat.reply_text(report)

    except Exception as e:
        if update.message:
            await update.message.reply_text(f"❌ Ошибка при получении истории расходов: {e}")
        elif update.callback_query:
            await update.callback_query.message.reply_text(f"❌ Ошибка при получении истории расходов: {e}")


def _is_expense_in_month(expense_date: str, target_month: str) -> bool:
    """
    Проверяет, относится ли дата расхода к целевому месяцу

    Args:
        expense_date: дата расхода в формате DD.MM.YYYY
        target_month: целевой месяц в формате MM.YYYY

    Returns:
        bool: True если расход относится к месяцу
    """
    try:
        # Парсим дату расхода
        if '.' in expense_date:
            day, month, year = expense_date.split('.')
        else:
            # Если формат отличается, пробуем другие варианты
            return False

        expense_month_year = f"{month}.{year}"
        return expense_month_year == target_month

    except (ValueError, AttributeError):
        return False


def _extract_category_from_store(store_name: str) -> str:
    """
    Извлекает категорию из названия магазина

    Args:
        store_name: название магазина (может содержать категорию в скобках)

    Returns:
        str: название категории
    """
    # Ищем категорию в скобках (для ручных вводов)
    match = re.search(r'\((.*?)\)', store_name)
    if match:
        return match.group(1).strip()

    # Определяем категорию по ключевым словам в названии магазина
    store_lower = store_name.lower()

    if any(word in store_lower for word in ['магнит', 'пятерочка', 'перекресток', 'ашан', 'окей', 'продукты', 'супермаркет']):
        return 'Продукты'
    elif any(word in store_lower for word in ['аптека', 'pharmacy']):
        return 'Здоровье'
    elif any(word in store_lower for word in ['кафе', 'ресторан', 'фастфуд', 'еда']):
        return 'Еда вне дома'
    elif any(word in store_lower for word in ['транспорт', 'такси', 'метро', 'автобус']):
        return 'Транспорт'
    elif any(word in store_lower for word in ['одежда', 'обувь', 'магазин']):
        return 'Одежда'
    elif any(word in store_lower for word in ['быт', 'хозтовары', 'товары']):
        return 'Бытовая химия'
    else:
        return 'Другое'


# Пример использования
if __name__ == "__main__":
    print("Модуль budget_handler загружен")
    print("Доступные функции:")
    print("1. handle_budget_status(update, context) - статус бюджета")
    print("2. handle_set_budget(update, context, text) - установка бюджета")
    print("3. handle_expense_history(update, context, month=None) - история расходов")
