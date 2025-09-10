from my_private_keys import TOKEN

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers import handle_message, handle_callback, handle_start

# Main function
def main():
    # Create app and transfer bot token
    application = Application.builder().token(TOKEN).build()

    # Add handler
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Run bot
    print("Бот запущен...")
    application.run_polling()

# Endpoint in program
if __name__ == "__main__":
    main()