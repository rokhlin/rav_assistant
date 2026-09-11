import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from config import settings

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        allowed = settings.allowed_users
        if not allowed:
            return await handler(event, data)

        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id and user_id not in allowed:
            logger.warning(f"Попытка несанкционированного доступа от user_id={user_id}")
            if isinstance(event, Message):
                await event.answer("⛔ У вас нет доступа к этому боту.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ запрещен.", show_alert=True)
            return

        return await handler(event, data)
