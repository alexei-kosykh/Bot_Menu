from get_access_table import COLUMN, sheetMenuToday as sheet
from keyboards import main_keyboard, inline_keyboard
import state
from utils.get_message import get_message
from my_private_keys import INLINE_BUTTONS

async def run(update, context, text):
    user_id = update.effective_user.id
    try:
        # Получаем сообщение универсально
        msg = update.message or (update.callback_query.message if update.callback_query else None)
        if not msg:
            return

        # Если пользователь только нажал кнопку — инструкцию выводим в handle_message,
        # сюда попадает уже ввод в формате "номер значение"
        if " " not in text:
            await msg.reply_text(
                "❌ Неверный формат. Введите номер строки и новое значение через пробел.\n"
                "Например: 3 Новая запись"
            )
            return

        # Разделяем ввод
        parts = text.split(" ", 1)
        row_num = int(parts[0])
        new_value = parts[1]

        # Обновляем ячейку в таблице
        sheet.update_cell(row_num, ord(COLUMN.lower()) - 96, new_value)

        await msg.reply_text("✅ Данные успешно обновлены!", reply_markup=main_keyboard)
        if user_id in state.USER_STATE:
            state.USER_STATE.pop(user_id)

    except ValueError:
        await msg.reply_text(
            "❌ Неверный формат. Введите номер строки и значение через пробел.",
        reply_markup=main_keyboard
    )
        if user_id in state.USER_STATE:
            state.USER_STATE.pop(user_id)

    except Exception as e:
        await msg.reply_text(f"❌ Ошибка при обновлении данных: {e}", reply_markup=main_keyboard)