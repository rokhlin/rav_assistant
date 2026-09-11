from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from bot.texts import get_text

def get_main_menu_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """
    Создает главное меню команд бота в виде постоянных кнопок на выбранном языке.
    """
    keyboard = [
        [
            KeyboardButton(text=get_text("btn_analyze", lang)),
            KeyboardButton(text=get_text("btn_translate", lang)),
        ],
        [
            KeyboardButton(text=get_text("btn_note", lang)),
            KeyboardButton(text=get_text("btn_save", lang)),
        ],
        [
            KeyboardButton(text=get_text("btn_status", lang)),
            KeyboardButton(text=get_text("btn_help", lang)),
        ],
        [
            KeyboardButton(text=get_text("btn_language", lang)),
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True
    )
