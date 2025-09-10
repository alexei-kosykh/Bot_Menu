import gspread

from my_private_keys import TOKEN, USERS
from keyboards import main_keyboard
import state
import edit_buying, get_ingredients_dish, get_menu_date, get_menu_today, find_recept, get_access_table

from telegram import Update, ReplyKeyboardMarkup

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from handlers import handle_message, handle_callback

# List of users that can work with app
ALLOWED_USERS = USERS

# Comand /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Checking user allow
    if user.username not in ALLOWED_USERS:
        await update.message.reply_text("❌ Доступ запрещен. Ваш username не в списке разрешенных.")
        return

    await update.message.reply_text(
        f"Привет, {user.first_name}! Выбери действие:",
        reply_markup=main_keyboard
    )

# Main function
def main():
    # Create app and transfer bot token
    application = Application.builder().token(TOKEN).build()

    # Add handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Run bot
    print("Бот запущен...")
    application.run_polling()

# Endpoint in program
if __name__ == "__main__":
    main()