from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает главное меню команд бота в виде постоянных кнопок.
    """
    keyboard = [
        [
            KeyboardButton(text="🔍 Анализ и перевод"),
            KeyboardButton(text="🌐 Перевод"),
        ],
        [
            KeyboardButton(text="📝 Новая заметка"),
            KeyboardButton(text="💾 Сохранить в облако"),
        ],
        [
            KeyboardButton(text="📊 Статус бота"),
            KeyboardButton(text="ℹ️ Справка"),
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True
    )
