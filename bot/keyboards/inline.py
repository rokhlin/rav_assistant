from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional
from bot.texts import get_text, SUPPORTED_LANGUAGES

def get_media_actions_keyboard(file_type: str = "doc", current_action: Optional[str] = None, lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Creates inline action buttons under sent file or image in the selected language.
    """
    buttons = []
    
    # Alternative action buttons
    row1 = []
    if current_action != "translate":
        row1.append(InlineKeyboardButton(text=get_text("inline_translate", lang), callback_data="act_translate"))
    if current_action != "analyze":
        row1.append(InlineKeyboardButton(text=get_text("inline_analyze", lang), callback_data="act_analyze"))
    if row1:
        buttons.append(row1)

    # Second row: Save to cloud and save as note
    row2 = [
        InlineKeyboardButton(text=get_text("inline_save_cloud", lang), callback_data="act_save_cloud"),
        InlineKeyboardButton(text=get_text("inline_save_note", lang), callback_data="act_save_note")
    ]
    buttons.append(row2)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Action cancellation button in the selected language."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=get_text("inline_cancel", lang), callback_data="act_cancel")]]
    )

def get_language_keyboard(current_lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Interface and translation language selection keyboard.
    """
    lang_flags = {
        "ru": "🇷🇺",
        "en": "🇬🇧",
        "he": "🇮🇱"
    }
    buttons = []
    for code, name in SUPPORTED_LANGUAGES.items():
        flag = lang_flags.get(code, "")
        marker = " ✓" if code == current_lang else ""
        btn_text = f"{flag} {name}{marker}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"lang_set:{code}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_note_share_keyboard(note_token: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Button to share note with another configured user.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text("inline_share_note", lang), callback_data=f"share_start:{note_token}")]
        ]
    )

def get_recipients_keyboard(note_token: str, current_user_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Displays list of users to share note with (excluding current sender).
    """
    from config import settings
    buttons = []
    
    users_map = settings.allowed_users_map
    for uid, name in users_map.items():
        if uid != current_user_id:
            btn_text = f"👤 {name}"
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"share_send:{uid}:{note_token}")])

    buttons.append([InlineKeyboardButton(text=get_text("inline_cancel", lang), callback_data="act_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_request_access_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard with Request Access button for unauthorized users."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text("btn_request_access", lang), callback_data="req_access")]
        ]
    )

def get_admin_request_keyboard(applicant_id: int, applicant_name: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard sent to admin with Approve and Reject buttons."""
    approve_text = get_text("admin_btn_approve", lang, name=applicant_name[:20])
    reject_text = get_text("admin_btn_reject", lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=approve_text, callback_data=f"adm_appr:{applicant_id}"),
                InlineKeyboardButton(text=reject_text, callback_data=f"adm_rejc:{applicant_id}")
            ]
        ]
    )

def get_admin_main_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Main admin panel keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text("admin_btn_users_list", lang), callback_data="adm_list")],
            [InlineKeyboardButton(text=get_text("admin_btn_add_user", lang), callback_data="adm_add")],
            [InlineKeyboardButton(text=get_text("admin_btn_close", lang), callback_data="adm_close")]
        ]
    )

def get_admin_users_list_keyboard(users: dict, lang: str = "ru") -> InlineKeyboardMarkup:
    """List of all users for admin to inspect."""
    buttons = []
    for uid_str, data in users.items():
        name = data.get("name", f"User {uid_str}")
        role_icon = "👑 " if data.get("role") == "admin" else "👤 "
        btn_text = f"{role_icon}{name} ({uid_str})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"adm_view:{uid_str}")])
    buttons.append([InlineKeyboardButton(text=get_text("admin_btn_add_user", lang), callback_data="adm_add")])
    buttons.append([InlineKeyboardButton(text=get_text("admin_btn_close", lang), callback_data="adm_close")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_user_card_keyboard(user_id: int, is_self: bool = False, lang: str = "ru") -> InlineKeyboardMarkup:
    """Actions for a specific user card."""
    row = [
        InlineKeyboardButton(text=get_text("admin_btn_edit_name", lang), callback_data=f"adm_ren:{user_id}")
    ]
    if not is_self:
        row.append(InlineKeyboardButton(text=get_text("admin_btn_delete_user", lang), callback_data=f"adm_del:{user_id}"))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row,
            [InlineKeyboardButton(text=get_text("admin_btn_back_list", lang), callback_data="adm_list")]
        ]
    )
