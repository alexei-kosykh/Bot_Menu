from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from my_private_keys import MAIN_MENU, INLINE_GET_MENU, INLINE_EDIT_MENU
from my_private_keys import TABLE_URL


main_keyboard = ReplyKeyboardMarkup(
    MAIN_MENU,
    resize_keyboard=True,
    one_time_keyboard=False,
    input_field_placeholder="Выберите действие"
)


def inline_keyboard(inline_button):
    keyboard = []
    for row in inline_button:
        keyboard.append([
            InlineKeyboardButton(**btn) for btn in row
        ])
    return InlineKeyboardMarkup(keyboard)

# menu_by_date_keyboard = InlineKeyboardMarkup([
#         [InlineKeyboardButton(inline_button, url=TABLE_URL)]
# ])
