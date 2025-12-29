from get_access_table import sheetMenuMounth as sheet
from telegram import Update
from telegram.ext import ContextTypes
from keyboards import main_keyboard, inline_keyboard
from my_private_keys import INLINE_GET_MENU
from utils.get_message import get_message

async def run(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        # Checking number
        if not text.isdigit():
            await update.message.reply_text(
                "❌ Введите число от 1 до 31.",
                reply_markup=main_keyboard
            )
            return

        day = int(text)
        if day < 1 or day > 31:
            await update.message.reply_text(
                f"❌ День должен быть от 1 до 31. Выберите действие:",
                reply_markup=inline_keyboard(INLINE_GET_MENU)
            )
            return

        # Get all values
        col_a = sheet.col_values(1)
        col_b = sheet.col_values(2)
        col_c = sheet.col_values(3)
        col_e = sheet.col_values(5)

        # Find all strings with number
        response = f"📅 Меню на *{day}* число:\n\n"
        found = False
        for i in range(len(col_a)):
            if col_a[i].strip() == str(day):
                b = col_b[i] if i < len(col_b) else ""
                c = col_c[i] if i < len(col_c) else ""
                e = col_e[i] if i < len(col_e) else ""
                response += f"*{b}* | {c}\n_{e}_\n\n"
                found = True

        msg = get_message(update)
        if not found:
          response = f"❌ Для {day} числа меню не найдено."

        await msg.reply_text(
        response,
        parse_mode="Markdown",
        reply_markup=inline_keyboard(INLINE_GET_MENU)
        )

    except Exception as e:
      await msg.reply_text(f"❌ Ошибка при получении меню: {e}", reply_markup=main_keyboard)