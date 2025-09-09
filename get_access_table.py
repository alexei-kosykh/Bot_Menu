SPREADSHEET_ID = "1wM3T35GQEuNaLbamOdcKvkiyIJjyFwzxnU_Mf8MwxNg"  # Замените на ID вашей Google таблицы
SHEET_NAME_IDEAS = "Идеи/план"  # Название листа в таблице
SHEET_NAME_MENU_TODAY = "Меню_Сегодня_Полное"  # Название листа в таблице
SHEET_NAME_BASE_RECEPTS = "База_рецептов"  # Название листа в таблице
COLUMN = "B"  # Столбец для редактирования (можно изменить)

import gspread
from google.oauth2.service_account import Credentials

def setup_google_sheets(SHEET_NAME):
    """
    Создает подключение к Google Sheets и возвращает объект Worksheet.
    """
    try:
        # Указываем области доступа
        scope = ["https://www.googleapis.com/auth/spreadsheets"]

        # Авторизация с помощью сервисного аккаунта
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        client = gspread.authorize(creds)

        # Открываем таблицу и лист
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        print(f"Успешно подключились к Google Таблице и вкладке {SHEET_NAME}")
        return sheet

    except Exception as e:
        print(f"Ошибка подключения к Google Таблице: {e}")
        return None

# Инициализация объекта sheet при импорте модуля
sheetMenuToday = setup_google_sheets(SHEET_NAME_MENU_TODAY)
sheetMenuBaseRecepts = setup_google_sheets(SHEET_NAME_BASE_RECEPTS)
