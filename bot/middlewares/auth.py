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

        # Allow access requests from unauthorized users
        if getattr(event, "data", None) == "req_access":
            return await handler(event, data)

        if user_id and not user_manager.is_allowed(user_id):
            logger.warning(f"Unauthorized access attempt from user_id={user_id}")
            lang = user_settings.get_language(user_id)
            if isinstance(event, CallbackQuery):
                await event.answer(get_text("err_auth_callback", lang), show_alert=True)
            elif hasattr(event, "answer"):
                text = get_text("access_restricted_prompt", lang, user_id=user_id)
                await event.answer(text, reply_markup=get_request_access_keyboard(lang), parse_mode="Markdown")
            return

        return await handler(event, data)
