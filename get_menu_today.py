from telegram import Update
from telegram.ext import ContextTypes

from get_access_table import sheetMenuToday as sheet
from utils.get_message import get_message
from keyboards import inline_keyboard
from my_private_keys import INLINE_GET_MENU

async def run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Получаем диапазоны
        col_a = sheet.get("A5:A10")
        col_b = sheet.get("B5:B10")
        col_d = sheet.get("D5:D10")

        # Функция для нормализации длины и извлечения значений
        def normalize(col, length=6):
            values = [row[0] if row else "" for row in col]  # берем значение или пустую строку
            # если колонка короче диапазона, дополняем пустыми строками
            while len(values) < length:
                values.append("")
            return values

        col_a = normalize(col_a)
        col_b = normalize(col_b)
        col_d = normalize(col_d)

        # Формируем таблицу
        response = "📋 Меню на сегодня:\n\n"
        for i in range(6):
            response += f"*{col_a[i]}* | {col_b[i]} \n_{col_d[i]}_\n\n"


        msg = get_message(update)
        if msg:
            await msg.reply_text(response, parse_mode="Markdown", reply_markup=inline_keyboard(INLINE_GET_MENU))
    except Exception as e:
        msg = get_message(update)
        if msg:
            await msg.reply_text(f"❌ Ошибка при чтении данных: {e}")
