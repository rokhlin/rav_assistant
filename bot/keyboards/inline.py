from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional

def get_media_actions_keyboard(file_type: str = "doc", current_action: Optional[str] = None) -> InlineKeyboardMarkup:
    """
    Создает инлайн-кнопки действий под отправленным файлом/картинкой.
    """
    buttons = []
    
    # Кнопки альтернативных действий
    row1 = []
    if current_action != "translate":
        row1.append(InlineKeyboardButton(text="🌐 Перевести", callback_data="act_translate"))
    if current_action != "analyze":
        row1.append(InlineKeyboardButton(text="🔍 Анализ и перевод", callback_data="act_analyze"))
    if row1:
        buttons.append(row1)

    # Вторая строка: Сохранение и создание заметки
    row2 = [
        InlineKeyboardButton(text="💾 В облако", callback_data="act_save_cloud"),
        InlineKeyboardButton(text="📝 Сохранить как заметку", callback_data="act_save_note")
    ]
    buttons.append(row2)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены активного действия/состояния."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="act_cancel")]]
    )
