import gspread

from my_private_keys import TOKEN, USERS, BUTTONS
import state
import edit_buying, get_ingredients_dish, get_menu_date, get_menu_today, get_recept, get_access_table

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# List of users that can work with app
ALLOWED_USERS = USERS

# Comand /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Checking user allow
    if user.username not in ALLOWED_USERS:
        await update.message.reply_text("❌ Доступ запрещен. Ваш username не в списке разрешенных.")
        return

    keyboard = BUTTONS
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"Привет, {user.first_name}! Выбери действие:",
        reply_markup=reply_markup
    )

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

    if text == "📅 Меню на сегодня":
        await get_menu_today.run(update, context)
        return

    if text == "✏️ Внести купленное":
        state.USER_STATE[user_id] = "WAITING_FOR_BUY_INPUT"
        await update.message.reply_text(
            "Введите номер строки и новое значение через пробел.\n"
            "Например: 3 Новая запись",
            parse_mode="Markdown"
        )
        return

    if text == "🔍 Найти ингредиенты":
        state.USER_STATE[user_id] = "WAITING_FOR_DISH"
        await update.message.reply_text("Введите название блюда:")
        return

    elif text:
        await update.message.reply_text("Используйте кнопки для выбора действия")

# Main function
def main():
    # Create app and transfer bot token
    application = Application.builder().token(TOKEN).build()

    # Add handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run bot
    print("Бот запущен...")
    application.run_polling()

# Endpoint in program
if __name__ == "__main__":
    main()