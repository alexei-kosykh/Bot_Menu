import gspread

from telegram import Update
from telegram.ext import ContextTypes

import state
from my_private_keys import USERS
from keyboards import main_keyboard, inline_keyboard
from my_private_keys import INLINE_GET_MENU, INLINE_EDIT_MENU, INLINE_RECEIPT_MENU, INLINE_BUDGET_MENU
import edit_buying, get_ingredients_dish, get_menu_date, get_menu_today, find_recept, get_access_table
import receipt_handler, budget_handler

# List of users that can work with app
ALLOWED_USERS = USERS

# Comand /start
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Checking user allow
    if user.username not in ALLOWED_USERS:
        await update.message.reply_text("❌ Доступ запрещен. Ваш username не в списке разрешенных.")
        return
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для работы с меню и покупками. Вот что я умею:\n\n"
        "📅 *Меню на сегодня* — покажу список блюд на текущий день.\n"
        "🗓 *Получить меню по дате* — можно ввести число (1–31), и я покажу меню на конкретный день.\n"
        "🔍 *Найти ингредиенты* — введи название блюда, и я пришлю список ингредиентов.\n"
        "✏️ *Внести купленное* — обновить список покупок в таблице.\n"
        "💰 *Внести чек* — сканирую QR-код или распознаю текст с фото чека.\n"
        "📊 *Бюджет на месяц* — устанавливаю бюджет и слежу за расходами.\n"
        "💳 *Ручной ввод расхода* — добавляю расходы вручную.\n\n"
        "👇 Выбирай действие с помощью кнопок ниже."
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=main_keyboard
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "menu_today":
        await get_menu_today.run(update, context)

    elif data == "menu_date":
        state.USER_STATE[user_id] = "WAITING_FOR_DATE"
        await query.message.reply_text("Введите число от 1 до 31:")

    elif data == "find_recept":
        state.USER_STATE[user_id] = "WAITING_FOR_DISH"
        await query.message.reply_text("Введите название блюда:")

    elif data == "edit_buying":
        state.USER_STATE[user_id] = "WAITING_FOR_BUY_INPUT"
        await query.message.reply_text(
            "Введите номер строки и новое значение через пробел.\n"
            "Например: 3 Новая запись",
            parse_mode="Markdown", reply_markup=main_keyboard
        )
        return

    elif data == "budget_status":
        await budget_handler.handle_budget_status(update, context)
        return

    elif data == "set_budget":
        state.USER_STATE[user_id] = "WAITING_FOR_BUDGET_AMOUNT"
        await query.message.reply_text("Введите сумму бюджета на текущий месяц:")
        return

    elif data == "expense_history":
        await budget_handler.handle_expense_history(update, context)
        return

    elif data == "expense_statistics":
        await budget_handler.handle_expense_statistics(update, context)
        return

    elif data == "send_receipt_photo":
        state.USER_STATE[user_id] = "WAITING_FOR_RECEIPT"
        await query.message.reply_text("Отправьте фото чека")
        return

    elif data == "manual_expense_input":
        state.USER_STATE[user_id] = "WAITING_FOR_MANUAL_EXPENSE"
        await query.message.reply_text(
            "Введите: Магазин | Сумма | Категория"
        )
        return

    else:
        await query.message.reply_text("❌ Неизвестная команда.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Checking allow
    if user.username not in ALLOWED_USERS:
        await update.message.reply_text("❌ Доступ запрещен")
        return

    # --- Checking state ---
    user_state = state.USER_STATE.get(user_id)
    if user_state == "WAITING_FOR_DISH":
        await get_ingredients_dish.run(update, context, text)
        state.USER_STATE.pop(user_id, None)
        return

    if user_state == "WAITING_FOR_BUY_INPUT":
        await edit_buying.run(update, context, text)
        return

    if user_state == "WAITING_FOR_DATE":
        await get_menu_date.run(update, context, text)
        state.USER_STATE.pop(user_id, None)
        return



    if user_state == "WAITING_FOR_BUDGET_AMOUNT":
        await budget_handler.handle_set_budget(update, context, text)
        state.USER_STATE.pop(user_id, None)
        return

    if user_state == "WAITING_FOR_MANUAL_EXPENSE":
        await receipt_handler.handle_manual_expense_async(update, context, text)
        state.USER_STATE.pop(user_id, None)
        return

    # Обработка подтверждения сохранения чека
    if text.lower() in ['да', 'yes', 'y', 'сохранить']:
        await receipt_handler.confirm_receipt_save(update, context)
        return
    elif text.lower() in ['нет', 'no', 'n', 'отмена']:
        if hasattr(context, 'user_data') and context.user_data and 'pending_receipt' in context.user_data:
            del context.user_data['pending_receipt']
            await update.message.reply_text("❌ Сохранение чека отменено.")
        else:
            await update.message.reply_text("❌ Нет активного чека для отмены.")
        return

    if text == "� Получить":
        await update.message.reply_text(
            "Что вы хотите получить?",
            reply_markup=inline_keyboard(INLINE_GET_MENU)
        )
        return

    elif text == "✏️ Изменить":
        await update.message.reply_text(
            "Что вы хотите изменить?",
            reply_markup=inline_keyboard(INLINE_EDIT_MENU)
        )
        return

    if text == "�💰 Внести чек":
        state.USER_STATE[user_id] = "WAITING_FOR_RECEIPT"
        await update.message.reply_text(
            "Отправьте фото чека с QR-кодом",
            reply_markup=inline_keyboard(INLINE_RECEIPT_MENU)
        )
        return

    if text == "📊 Бюджет на месяц":
        await update.message.reply_text(
            "Управление бюджетом:",
            reply_markup=inline_keyboard(INLINE_BUDGET_MENU)
        )
        return

    if text == "💳 Ручной ввод расхода":
        state.USER_STATE[user_id] = "WAITING_FOR_MANUAL_EXPENSE"
        await update.message.reply_text(
            "Введите данные в формате:\nМагазин | Сумма | Категория\n"
            "Например: Пятерочка | 1500 | Продукты"
        )
        return

    # if text == "✏️ Внести купленное":
    #     state.USER_STATE[user_id] = "WAITING_FOR_BUY_INPUT"
    #     await update.message.reply_text(
    #         "Введите номер строки и новое значение через пробел.\n"
    #         "Например: 3 Новая запись",
    #         parse_mode="Markdown", reply_markup=main_keyboard
    #     )
    #     return

    # if text == "🔍 Найти ингредиенты":
    #     state.USER_STATE[user_id] = "WAITING_FOR_DISH"
    #     await update.message.reply_text("Введите название блюда:", reply_markup=main_keyboard)
    #     return

    # if text == "🗓 Получить меню по дате":
    #     state.USER_STATE[user_id] = "WAITING_FOR_DATE"
    #     await update.message.reply_text("Введите число (от 1 до 31):")
    #     return

    elif text:
        await update.message.reply_text("Используйте кнопки для выбора действия", reply_markup=main_keyboard)
