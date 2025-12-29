import gspread

from telegram import Update
from telegram.ext import ContextTypes

import state
from my_private_keys import USERS
from keyboards import main_keyboard, inline_keyboard
from my_private_keys import INLINE_GET_MENU, INLINE_EDIT_MENU
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
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для работы с меню и покупками. Вот что я умею:\n\n"
        "📅 *Меню на сегодня* — покажу список блюд на текущий день.\n"
        "🗓 *Получить меню по дате* — можно ввести число (1–31), и я покажу меню на конкретный день.\n"
        "🔍 *Найти ингредиенты* — введи название блюда, и я пришлю список ингредиентов.\n"
        "✏️ *Внести купленное* — обновить список покупок в таблице.\n\n"
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

    if text == "🔍 Получить":
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
