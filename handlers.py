import gspread

from telegram import Update
from telegram.ext import ContextTypes

import state
from my_private_keys import USERS
from keyboards import main_keyboard
import edit_buying, get_ingredients_dish, get_menu_date, get_menu_today, find_recept, get_access_table

# List of users that can work with app
ALLOWED_USERS = USERS

# Comand /start
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Checking user allow
    if user.username not in ALLOWED_USERS:
        await update.message.reply_text("❌ Доступ запрещен. Ваш username не в списке разрешенных.")
        return

    await update.message.reply_text(
        f"Привет, {user.first_name}! Выбери действие:",
        reply_markup=main_keyboard
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # обязательно! закрывает "часики" у пользователя

    user_id = query.from_user.id
    data = query.data  # вот что ты задаёшь в InlineKeyboardButton(callback_data="...")

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
        await edit_buying.run(update, context, "✏️ Внести купленное")

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
    if state.USER_STATE.get(user_id) == "WAITING_FOR_DISH":
        await get_ingredients_dish.run(update, context, text)
        state.USER_STATE.pop(user_id)
        return

    if state.USER_STATE.get(user_id) == "WAITING_FOR_BUY_INPUT":
        await edit_buying.run(update, context, text)
        return

    if state.USER_STATE.get(user_id) == "WAITING_FOR_DATE":
        await get_menu_date.run(update, context, text)
        state.USER_STATE.pop(user_id, None)
        return

    if text == "📅 Меню на сегодня":
        await get_menu_today.run(update, context)
        return

    if text == "✏️ Внести купленное":
        state.USER_STATE[user_id] = "WAITING_FOR_BUY_INPUT"
        await update.message.reply_text(
            "Введите номер строки и новое значение через пробел.\n"
            "Например: 3 Новая запись",
            parse_mode="Markdown", reply_markup=main_keyboard
        )
        return

    if text == "🔍 Найти ингредиенты":
        state.USER_STATE[user_id] = "WAITING_FOR_DISH"
        await update.message.reply_text("Введите название блюда:", reply_markup=main_keyboard)
        return

    if text == "🗓 Получить меню по дате":
        state.USER_STATE[user_id] = "WAITING_FOR_DATE"
        await update.message.reply_text("Введите число (от 1 до 31):")
        return

    elif text:
        await update.message.reply_text("Используйте кнопки для выбора действия", reply_markup=main_keyboard)
