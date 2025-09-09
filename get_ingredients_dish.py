from get_access_table import sheetMenuBaseRecepts as sheet
from telegram import Update
from telegram.ext import ContextTypes
import state

async def run(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    text = text.strip()
    user_id = update.effective_user.id

    try:
            # Получаем все значения колонки E (названия блюд)
            dishes_col = sheet.col_values(5)  # E - 5-я колонка

            # Ищем строку с нужным блюдом
            try:
                start_row = dishes_col.index(text) + 1  # Google Sheets 1-indexed
            except ValueError:
                await update.message.reply_text(f"❌ Блюдо '{text}' не найдено")
                return


            # Находим строку следующего блюда
            end_row = len(dishes_col) + 1
            for i in range(start_row, len(dishes_col)):
                if dishes_col[i].strip():  # если не пустая ячейка, значит новое блюдо
                    end_row = i + 1
                    break

            # Получаем диапазоны колонок F, G, H
            range_f = f"F{start_row}:F{end_row-1}"
            range_g = f"G{start_row}:G{end_row-1}"
            range_h = f"H{start_row}:H{end_row-1}"

            col_f = sheet.get(range_f)
            col_g = sheet.get(range_g)
            col_h = sheet.get(range_h)

            # Нормализуем длину
            length = max(len(col_f), len(col_g), len(col_h))
            def normalize(col):
                values = [row[0] if row else "" for row in col]
                while len(values) < length:
                    values.append("")
                return values

            col_f = normalize(col_f)
            col_g = normalize(col_g)
            col_h = normalize(col_h)

            # Формируем ответ
            response = f"📋 *Ингредиенты для {text}:*\n\n"
            for i in range(length):
                response += f"{col_f[i]} | {col_g[i]} | {col_h[i]}\n"

            await update.message.reply_text(response, parse_mode="Markdown")
            if user_id in state.USER_STATE:
              state.USER_STATE.pop(user_id)
            return

    except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при получении ингредиентов: {e}")
