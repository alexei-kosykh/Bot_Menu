"""
Обработчики для работы с чеками и ручным вводом расходов
"""

import io
import re
from datetime import datetime
from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes

from receipt_scanner import decode_qr_from_image, parse_receipt_from_qr, ocr_fallback
from expense_manager import add_expense, update_budget, get_budget_info
from budget_commands import get_budget_status, get_budget_notifications


async def handle_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает фото чека от пользователя

    Args:
        update: объект обновления Telegram
        context: контекст бота
    """
    try:
        # Получаем фото (берем самое большое разрешение)
        if not update.message.photo:
            await update.message.reply_text("❌ Пожалуйста, отправьте фото чека.")
            return

        photo = update.message.photo[-1]

        # Скачиваем файл
        file = await context.bot.get_file(photo.file_id)
        file_bytes = await file.download_as_bytearray()

        # Валидация размера файла (макс. 10 МБ)
        if len(file_bytes) > 10 * 1024 * 1024:
            await update.message.reply_text("❌ Размер файла превышает 10 МБ. Пожалуйста, загрузите изображение меньшего размера.")
            return

        # Преобразуем в bytes для обработки
        image_bytes = bytes(file_bytes)

        await update.message.reply_text("🔍 Распознаю чек... Пожалуйста, подождите.")

        # Сначала пытаемся декодировать QR-код
        try:
            qr_data = decode_qr_from_image(image_bytes)
            await update.message.reply_text("✅ QR-код найден! Извлекаю данные чека...")

            # Парсим данные чека из QR-кода
            receipt_data = parse_receipt_from_qr(qr_data)

            if receipt_data and receipt_data.get('total', 0) > 0:
                await _process_receipt_data(update, receipt_data, method="QR", context=context)
                return
            else:
                await update.message.reply_text("⚠️ Не удалось извлечь данные из QR-кода. Пробую OCR...")
        except ValueError:
            # QR-код не найден, пробуем OCR
            await update.message.reply_text("📷 QR-код не найден. Пробую распознать текст...")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при обработке QR-кода: {e}")
            return

        # Если QR не сработал, пробуем OCR
        try:
            ocr_data = ocr_fallback(image_bytes)

            if ocr_data and (ocr_data.get('shop') or ocr_data.get('total')):
                # Создаем структурированные данные для OCR
                receipt_data = {
                    'date': ocr_data.get('date', datetime.now().strftime('%d.%m.%Y %H:%M')),
                    'shop': ocr_data.get('shop', 'Неизвестно (OCR)'),
                    'total': ocr_data.get('total', 0),
                    'items': [],  # OCR не предоставляет детальные товары
                    'method': 'OCR',
                    'raw_text': ocr_data.get('raw_text', '')
                }
                await _process_receipt_data(update, receipt_data, method="OCR", context=context)
            else:
                await update.message.reply_text("❌ Не удалось распознать данные чека. Попробуйте ввести данные вручную.")
        except ValueError as e:
            await update.message.reply_text(f"❌ {e}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при OCR-распознавании: {e}")

    except Exception as e:
        await update.message.reply_text(f"❌ Произошла ошибка при обработке фото: {e}")


async def _process_receipt_data(update: Update, receipt_data: Dict[str, Any], method: str, context: ContextTypes.DEFAULT_TYPE = None) -> None:
    """
    Обрабатывает распознанные данные чека и предлагает пользователю подтверждение

    Args:
        update: объект обновления Telegram
        receipt_data: данные чека
        method: метод распознавания ("QR" или "OCR")
    """
    try:
        # Валидация данных
        receipt_date = receipt_data.get('date', datetime.now().strftime('%d.%m.%Y'))
        total = receipt_data.get('total', 0)

        # Валидация формата даты
        try:
            datetime.strptime(receipt_date, '%d.%m.%Y')
        except ValueError:
            await update.message.reply_text("❌ Неверный формат даты. Используйте DD.MM.YYYY")
            return

        # Валидация положительной суммы
        if total <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительным числом.")
            return

        # Формируем сообщение с данными чека
        message = f"""
📄 **Данные чека ({method}):**

🏪 **Магазин:** {receipt_data.get('shop', 'Неизвестно')}
📅 **Дата:** {receipt_date}
💰 **Сумма:** {total:,.0f} руб.
"""

        if receipt_data.get('items') and len(receipt_data['items']) > 0:
            message += "\n🛒 **Товары:**\n"
            for item in receipt_data['items'][:5]:  # Показываем максимум 5 товаров
                message += f"• {item.get('name', '')} - {item.get('sum', 0):.2f} руб.\n"
            if len(receipt_data['items']) > 5:
                message += f"... и ещё {len(receipt_data['items']) - 5} товаров\n"

        message += "\n✅ Всё верно? Отправьте 'да' для сохранения или 'нет' для отмены."

        # Сохраняем данные во временном хранилище
        if not hasattr(context, 'user_data') or context.user_data is None:
            context.user_data = {}

        context.user_data['pending_receipt'] = {
            'date': receipt_date,
            'store': receipt_data.get('shop', 'Неизвестно'),
            'items': receipt_data.get('items', []),
            'total': total,
            'method': method
        }

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обработке данных чека: {e}")


async def confirm_receipt_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Подтверждает и сохраняет данные чека

    Args:
        update: объект обновления Telegram
        context: контекст бота
    """
    try:
        if not hasattr(context, 'user_data') or 'pending_receipt' not in context.user_data:
            await update.message.reply_text("❌ Нет данных чека для сохранения.")
            return

        receipt_data = context.user_data['pending_receipt']

        # Сохраняем расход
        success = add_expense(
            date=receipt_data['date'],
            store=receipt_data['store'],
            items=receipt_data['items'],
            total=receipt_data['total']
        )

        if not success:
            await update.message.reply_text("❌ Ошибка при сохранении расхода.")
            return

        # Обновляем бюджет
        current_month = datetime.now().strftime('%m.%Y')
        budget_updated = update_budget(current_month, receipt_data['total'])

        # Получаем статус бюджета
        budget_status = get_budget_status()

        # Получаем уведомления о бюджете
        budget_notifications = get_budget_notifications()

        # Формируем ответ
        response = f"""
✅ **Расход сохранен!**

💰 Сумма: {receipt_data['total']:,.0f} руб.
🏪 Магазин: {receipt_data['store']}
📅 Дата: {receipt_data['date']}
"""

        if budget_status:
            response += f"\n{budget_status}"
        else:
            response += "\n⚠️ Не удалось получить статус бюджета."

        await update.message.reply_text(response)

        # Отправляем уведомления о бюджете отдельно, если есть
        if budget_notifications:
            await update.message.reply_text(budget_notifications)

        # Очищаем временные данные
        del context.user_data['pending_receipt']

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при сохранении чека: {e}")


async def handle_manual_expense_async(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """
    Обрабатывает ручной ввод расхода

    Args:
        update: объект обновления Telegram
        context: контекст бота
        text: текст в формате "Магазин | Сумма | Категория"
    """
    try:
        # Парсим ввод формата: "Магазин | Сумма | Категория"
        parts = [part.strip() for part in text.split('|')]

        if len(parts) != 3:
            await update.message.reply_text("❌ Неверный формат. Используйте: 'Магазин | Сумма | Категория'\nПример: 'Магнит | 500.50 | Продукты'")
            return

        store, amount_str, category = parts

        # Валидируем магазин
        if not store or len(store) < 2:
            await update.message.reply_text("❌ Название магазина должно содержать минимум 2 символа.")
            return

        # Валидируем сумму
        try:
            amount = float(amount_str.replace(',', '.'))
            if amount <= 0:
                await update.message.reply_text("❌ Сумма должна быть положительным числом.")
                return
        except ValueError:
            await update.message.reply_text("❌ Сумма должна быть числом (например: 500.50 или 500,50).")
            return

        # Валидируем категорию
        if not category or len(category) < 2:
            await update.message.reply_text("❌ Название категории должно содержать минимум 2 символа.")
            return

        # Получаем текущую дату
        current_date = datetime.now().strftime('%d.%m.%Y')

        # Сохраняем расход (без детальных товаров)
        success = add_expense(
            date=current_date,
            store=f"{store} ({category})",  # Добавляем категорию к названию магазина
            items=[],  # Ручной ввод не имеет детальных товаров
            total=amount
        )

        if not success:
            await update.message.reply_text("❌ Ошибка при сохранении расхода.")
            return

        # Обновляем бюджет
        current_month = datetime.now().strftime('%m.%Y')
        budget_updated = update_budget(current_month, amount)

        # Получаем статус бюджета
        budget_status = get_budget_status()

        # Получаем уведомления о бюджете
        budget_notifications = get_budget_notifications()

        # Формируем ответ
        response = f"""
✅ **Расход добавлен вручную!**

💰 Сумма: {amount:,.0f} руб.
🏪 Магазин: {store}
📂 Категория: {category}
📅 Дата: {current_date}
"""

        if budget_status:
            response += f"\n{budget_status}"
        else:
            response += "\n⚠️ Не удалось получить статус бюджета."

        await update.message.reply_text(response)

        # Отправляем уведомления о бюджете отдельно, если есть
        if budget_notifications:
            await update.message.reply_text(budget_notifications)

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обработке ручного ввода: {e}")


# Пример использования
if __name__ == "__main__":
    print("Модуль receipt_handler загружен")
    print("Доступные функции:")
    print("1. handle_receipt_photo(update, context) - обработка фото чека")
    print("2. handle_manual_expense(update, context, text) - ручной ввод расхода")
    print("3. confirm_receipt_save(update, context) - подтверждение сохранения чека")
