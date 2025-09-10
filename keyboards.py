from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from my_private_keys import BUTTONS, INLINE_BUTTONS, BUTTON_REPEAT_MENU_DATE
from my_private_keys import TABLE_URL


main_keyboard = ReplyKeyboardMarkup(
    BUTTONS,
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

menu_by_date_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton(BUTTON_REPEAT_MENU_DATE, url=TABLE_URL)]
])
