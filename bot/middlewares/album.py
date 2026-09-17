import asyncio
import logging
from typing import Callable, Dict, Any, Awaitable, List
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

logger = logging.getLogger(__name__)

class MediaGroupMiddleware(BaseMiddleware):
    """
    Middleware that debounces and aggregates multiple messages sharing
    the same `media_group_id` into an `album` list in the handler data context.
    """
    def __init__(self, latency: float = 0.8):
        self.latency = latency
        self.albums: Dict[str, List[Message]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not getattr(event, "media_group_id", None):
            return await handler(event, data)

        mg_id = event.media_group_id
        if mg_id not in self.albums:
            self.albums[mg_id] = [event]
        else:
            self.albums[mg_id].append(event)

        # Wait for potential subsequent messages in the media group
        await asyncio.sleep(self.latency)

        # The last message of the group pops the collected album and forwards to handler
        if mg_id in self.albums and self.albums[mg_id][-1] == event:
            album_messages = self.albums.pop(mg_id)
            data["album"] = album_messages
            logger.info(f"Processed media group {mg_id} with {len(album_messages)} items")
            return await handler(event, data)

        return None
