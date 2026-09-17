import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from bot.services.user_manager import user_manager
from bot.services.user_settings import user_settings
from bot.keyboards.inline import get_request_access_keyboard
from bot.texts import get_text

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if hasattr(event, "from_user") and event.from_user:
            user_id = event.from_user.id

        # Bootstrap first user as creator/admin if system is completely fresh and has no admins
        if user_id and not user_manager.has_any_admins():
            if hasattr(event, "from_user") and event.from_user:
                full_name = f"{event.from_user.first_name or ''} {event.from_user.last_name or ''}".strip() or f"User {user_id}"
                user_manager.bootstrap_first_user_as_admin(
                    user_id=user_id,
                    name=full_name,
                    username=event.from_user.username
                )
                logger.info(f"User {user_id} ({full_name}) registered as the first bot creator/admin.")
                return await handler(event, data)

        # Allow access requests from unauthorized users
        if getattr(event, "data", None) == "req_access":
            return await handler(event, data)

        if user_id and not user_manager.is_allowed(user_id):
            logger.warning(f"Unauthorized access attempt from user_id={user_id}")
            lang = user_settings.get_language(user_id)
            if isinstance(event, CallbackQuery):
                await event.answer(get_text("err_auth_callback", lang), show_alert=True)
            elif hasattr(event, "answer"):
                bot = data.get("bot")
                from bot.handlers.admin import send_access_request_to_admins, _pending_access_requests
                if user_id not in _pending_access_requests and bot and hasattr(event, "from_user") and event.from_user:
                    await send_access_request_to_admins(bot, event.from_user)
                    text = get_text("access_requested_auto", lang, user_id=user_id)
                else:
                    text = get_text("access_already_requested_msg", lang, user_id=user_id)
                await event.answer(text, parse_mode="Markdown")
            return

        return await handler(event, data)
