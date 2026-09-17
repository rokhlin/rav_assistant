import logging
from typing import Set, Any
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.states import BotStates
from bot.services.user_manager import user_manager
from bot.services.user_settings import user_settings
from bot.keyboards.inline import (
    get_admin_main_keyboard,
    get_admin_users_list_keyboard,
    get_admin_user_card_keyboard,
    get_admin_request_keyboard,
)
from bot.texts import get_text
from bot.utils.telegram_helpers import safe_edit_text

logger = logging.getLogger(__name__)
router = Router(name="admin_router")

# Track pending access requests in memory to prevent duplicate spam
_pending_access_requests: Set[int] = set()

# ---------------------------------------------------------------------------
# Access Request Handlers (for unauthorized users)
# ---------------------------------------------------------------------------

async def send_access_request_to_admins(bot: Bot, user: Any) -> bool:
    """Send access request notification to all administrators."""
    user_id = user.id
    if user_manager.is_allowed(user_id):
        return False
    if user_id in _pending_access_requests:
        return False

    _pending_access_requests.add(user_id)

    full_name = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip() or f"User {user_id}"
    username_str = f"@{user.username}" if getattr(user, "username", None) else "—"

    admin_ids = user_manager.get_admin_ids()
    notified_any = False
    for aid in admin_ids:
        admin_lang = user_settings.get_language(aid)
        alert_text = get_text(
            "admin_new_request_notification",
            admin_lang,
            name=full_name,
            username=username_str,
            user_id=user_id
        )
        kb = get_admin_request_keyboard(applicant_id=user_id, applicant_name=getattr(user, "first_name", None) or full_name, lang=admin_lang)
        try:
            await bot.send_message(chat_id=aid, text=alert_text, reply_markup=kb, parse_mode="Markdown")
            notified_any = True
        except Exception as e:
            logger.warning(f"Failed to send access request alert to admin {aid}: {e}")

    logger.info(f"Access request from user {user_id} ({full_name}) sent to admins: {notified_any}")
    return notified_any


@router.callback_query(F.data == "req_access")
async def callback_request_access(query: CallbackQuery, bot: Bot, lang: str = "ru"):
    """Handle unauthorized user pressing 'Request Access' button."""
    user = query.from_user
    if not user:
        await query.answer()
        return

    user_id = user.id
    if user_manager.is_allowed(user_id):
        await query.answer(get_text("user_access_approved", lang), show_alert=True)
        return

    if user_id in _pending_access_requests:
        await query.answer(get_text("access_already_requested", lang), show_alert=True)
        return

    await send_access_request_to_admins(bot, user)

    # Confirm to applicant
    await query.answer()
    success_text = get_text("access_requested_success", lang)
    await safe_edit_text(query.message, success_text, parse_mode="Markdown")


@router.callback_query(F.data.startswith("adm_appr:"))
async def callback_approve_request(query: CallbackQuery, bot: Bot, lang: str = "ru"):
    """Administrator approves user access request."""
    if not user_manager.is_admin(query.from_user.id):
        await query.answer("Access denied", show_alert=True)
        return

    applicant_id_str = query.data.split(":", 1)[1]
    if not applicant_id_str.isdigit():
        await query.answer()
        return

    applicant_id = int(applicant_id_str)
    _pending_access_requests.discard(applicant_id)

    # Determine applicant's name from original notification or default
    applicant_name = f"User {applicant_id}"
    if query.message and query.message.text:
        for line in query.message.text.split("\n"):
            if "Имя" in line or "Name" in line or "שם" in line:
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    applicant_name = parts[1].strip()
                    break

    # Add to dynamic user store
    user_manager.add_user(
        user_id=applicant_id,
        name=applicant_name,
        role="user"
    )

    # Notify administrator
    msg = get_text("admin_request_approved_msg", lang, name=applicant_name, user_id=applicant_id)
    await safe_edit_text(query.message, msg, parse_mode="Markdown")
    await query.answer("✓")

    # Notify applicant
    applicant_lang = user_settings.get_language(applicant_id)
    try:
        await bot.send_message(
            chat_id=applicant_id,
            text=get_text("user_access_approved", applicant_lang),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Failed to notify applicant {applicant_id} of approval: {e}")


@router.callback_query(F.data.startswith("adm_rejc:"))
async def callback_reject_request(query: CallbackQuery, lang: str = "ru"):
    """Administrator rejects user access request."""
    if not user_manager.is_admin(query.from_user.id):
        await query.answer("Access denied", show_alert=True)
        return

    applicant_id_str = query.data.split(":", 1)[1]
    if applicant_id_str.isdigit():
        _pending_access_requests.discard(int(applicant_id_str))

    msg = get_text("admin_request_rejected_msg", lang, name=f"ID {applicant_id_str}", user_id=applicant_id_str)
    await safe_edit_text(query.message, msg, parse_mode="Markdown")
    await query.answer("✓")


# ---------------------------------------------------------------------------
# Admin Panel Handlers
# ---------------------------------------------------------------------------

@router.message(Command("admin"))
async def cmd_admin_panel(message: Message, state: FSMContext, lang: str = "ru"):
    """Open admin panel."""
    await state.clear()
    if not user_manager.is_admin(message.from_user.id):
        return

    users_count = len(user_manager.get_all_users())
    text = get_text("admin_panel_title", lang, count=users_count)
    await message.answer(text, reply_markup=get_admin_main_keyboard(lang), parse_mode="Markdown")


@router.callback_query(F.data == "adm_main")
async def callback_admin_main(query: CallbackQuery, state: FSMContext, lang: str = "ru"):
    """Return to admin panel main menu."""
    await state.clear()
    if not user_manager.is_admin(query.from_user.id):
        await query.answer()
        return

    users_count = len(user_manager.get_all_users())
    text = get_text("admin_panel_title", lang, count=users_count)
    await safe_edit_text(query.message, text, reply_markup=get_admin_main_keyboard(lang), parse_mode="Markdown")
    await query.answer()


@router.callback_query(F.data == "adm_list")
async def callback_admin_list_users(query: CallbackQuery, state: FSMContext, lang: str = "ru"):
    """Show list of all users."""
    await state.clear()
    if not user_manager.is_admin(query.from_user.id):
        await query.answer()
        return

    users = user_manager.get_all_users()
    kb = get_admin_users_list_keyboard(users, lang=lang)
    text = get_text("admin_panel_title", lang, count=len(users))
    await safe_edit_text(query.message, text, reply_markup=kb, parse_mode="Markdown")
    await query.answer()


@router.callback_query(F.data.startswith("adm_view:"))
async def callback_admin_view_user(query: CallbackQuery, lang: str = "ru"):
    """View user details card."""
    if not user_manager.is_admin(query.from_user.id):
        await query.answer()
        return

    uid_str = query.data.split(":", 1)[1]
    if not uid_str.isdigit():
        await query.answer()
        return

    uid_int = int(uid_str)
    user_info = user_manager.get_user(uid_int)
    if not user_info:
        await query.answer("User not found", show_alert=True)
        return

    is_self = (uid_int == query.from_user.id)
    text = get_text(
        "admin_user_card",
        lang,
        name=user_info.get("name", f"User {uid_str}"),
        user_id=uid_str,
        role=user_info.get("role", "user"),
        username=user_info.get("username", "—") or "—",
        added_at=user_info.get("added_at", "—")
    )
    kb = get_admin_user_card_keyboard(uid_int, is_self=is_self, lang=lang)
    await safe_edit_text(query.message, text, reply_markup=kb, parse_mode="Markdown")
    await query.answer()


@router.callback_query(F.data.startswith("adm_del:"))
async def callback_admin_delete_user(query: CallbackQuery, lang: str = "ru"):
    """Revoke user access."""
    if not user_manager.is_admin(query.from_user.id):
        await query.answer()
        return

    uid_str = query.data.split(":", 1)[1]
    if not uid_str.isdigit():
        await query.answer()
        return

    uid_int = int(uid_str)
    if uid_int == query.from_user.id:
        await query.answer(get_text("admin_cannot_delete_self", lang), show_alert=True)
        return

    user_name = user_manager.get_user_name(uid_int)
    user_manager.remove_user(uid_int)

    await query.answer(get_text("admin_user_deleted_success", lang, name=user_name, user_id=uid_str), show_alert=True)

    # Return to updated user list
    users = user_manager.get_all_users()
    kb = get_admin_users_list_keyboard(users, lang=lang)
    text = get_text("admin_panel_title", lang, count=len(users))
    await safe_edit_text(query.message, text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("adm_ren:"))
async def callback_admin_start_rename(query: CallbackQuery, state: FSMContext, lang: str = "ru"):
    """Start rename user flow."""
    if not user_manager.is_admin(query.from_user.id):
        await query.answer()
        return

    uid_str = query.data.split(":", 1)[1]
    if not uid_str.isdigit():
        await query.answer()
        return

    uid_int = int(uid_str)
    await state.set_state(BotStates.admin_waiting_for_rename)
    await state.update_data(target_user_id=uid_int)

    prompt = get_text("admin_prompt_rename", lang, user_id=uid_str)
    await query.message.reply(prompt, parse_mode="Markdown")
    await query.answer()


@router.message(BotStates.admin_waiting_for_rename, F.text)
async def handle_rename_input(message: Message, state: FSMContext, lang: str = "ru"):
    """Process new name input."""
    data = await state.get_data()
    target_uid = data.get("target_user_id")
    new_name = message.text.strip()

    if target_uid and new_name:
        user_manager.update_user_name(target_uid, new_name)
        confirm_text = get_text("admin_user_renamed_success", lang, name=new_name)
        await message.answer(confirm_text, parse_mode="Markdown")

    await state.clear()


@router.callback_query(F.data == "adm_add")
async def callback_admin_start_add_user(query: CallbackQuery, state: FSMContext, lang: str = "ru"):
    """Start manual user addition flow."""
    if not user_manager.is_admin(query.from_user.id):
        await query.answer()
        return

    await state.set_state(BotStates.admin_waiting_for_new_user)
    prompt = get_text("admin_prompt_new_user", lang)
    await query.message.reply(prompt, parse_mode="Markdown")
    await query.answer()


@router.message(BotStates.admin_waiting_for_new_user, F.text)
async def handle_add_user_input(message: Message, state: FSMContext, lang: str = "ru"):
    """Process new user ID and Name input."""
    raw = message.text.strip()
    uid = None
    name = ""

    if ":" in raw:
        parts = raw.split(":", 1)
        if parts[0].strip().isdigit():
            uid = int(parts[0].strip())
            name = parts[1].strip()
    elif " " in raw:
        parts = raw.split(" ", 1)
        if parts[0].strip().isdigit():
            uid = int(parts[0].strip())
            name = parts[1].strip()
    elif raw.isdigit():
        uid = int(raw)
        name = f"User {uid}"

    if not uid:
        await message.answer(get_text("err_invalid_user_format", lang))
        return

    user_manager.add_user(uid, name=name, role="user")
    confirm_text = get_text("admin_user_added_success", lang, name=name, user_id=uid)
    await message.answer(confirm_text, parse_mode="Markdown")
    await state.clear()


@router.callback_query(F.data == "adm_close")
async def callback_admin_close(query: CallbackQuery, state: FSMContext):
    """Close admin panel."""
    await state.clear()
    try:
        await query.message.delete()
    except Exception:
        pass
    await query.answer()
