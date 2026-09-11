import logging
from typing import List, Optional
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
from bot.texts import get_text

logger = logging.getLogger(__name__)

def split_text(text: str, max_chunk_size: int = 3800) -> List[str]:
    """
    Splits long text into chunks by paragraph or line boundaries,
    preserving formatting and sentences.
    """
    if not text:
        return []
    if len(text) <= max_chunk_size:
        return [text]

    chunks = []
    current_chunk = []
    current_len = 0

    lines = text.split("\n")
    for line in lines:
        line_len = len(line) + 1  # Account for newline
        if current_len + line_len > max_chunk_size and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_len = 0

        # If a single line exceeds max_chunk_size
        if len(line) > max_chunk_size:
            words = line.split(" ")
            sub_chunk = []
            sub_len = 0
            for word in words:
                if sub_len + len(word) + 1 > max_chunk_size and sub_chunk:
                    chunks.append(" ".join(sub_chunk))
                    sub_chunk = []
                    sub_len = 0
                sub_chunk.append(word)
                sub_len += len(word) + 1
            if sub_chunk:
                current_chunk.append(" ".join(sub_chunk))
                current_len += len(" ".join(sub_chunk)) + 1
        else:
            current_chunk.append(line)
            current_len += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks

async def safe_edit_text(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = "Markdown"
) -> Message:
    """
    Safe message edit.
    Falls back to plain text if Telegram Markdown parsing fails.
    """
    try:
        return await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        err_msg = str(e).lower()
        if "entity" in err_msg or "entities" in err_msg or "parse" in err_msg:
            logger.warning(f"Telegram Markdown parse error in edit_text: {e}. Falling back to plain text.")
            return await message.edit_text(text, reply_markup=reply_markup, parse_mode=None)
        raise

async def safe_answer(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = "Markdown"
) -> Message:
    """
    Safe message answer.
    Falls back to plain text if Telegram Markdown parsing fails.
    """
    try:
        return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        err_msg = str(e).lower()
        if "entity" in err_msg or "entities" in err_msg or "parse" in err_msg:
            logger.warning(f"Telegram Markdown parse error in answer: {e}. Falling back to plain text.")
            return await message.answer(text, reply_markup=reply_markup, parse_mode=None)
        raise

async def safe_reply(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = "Markdown"
) -> Message:
    """
    Safe message reply.
    Falls back to plain text if Telegram Markdown parsing fails.
    """
    try:
        return await message.reply(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        err_msg = str(e).lower()
        if "entity" in err_msg or "entities" in err_msg or "parse" in err_msg:
            logger.warning(f"Telegram Markdown parse error in reply: {e}. Falling back to plain text.")
            return await message.reply(text, reply_markup=reply_markup, parse_mode=None)
        raise

async def send_chunked_response(
    message: Message,
    status_msg: Message,
    full_text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    lang: str = "ru"
):
    """
    Splits long AI response into chunks and sends them to the user,
    handling markdown formatting resilience.
    """
    chunks = split_text(full_text, max_chunk_size=3800)
    if not chunks:
        empty_error = get_text("err_empty_ai_response", lang)
        await safe_edit_text(status_msg, empty_error, reply_markup=reply_markup)
        return

    # Edit the first chunk into the status message
    first_markup = reply_markup if len(chunks) == 1 else None
    await safe_edit_text(status_msg, chunks[0], reply_markup=first_markup)

    # Send any remaining chunks as new messages
    for i, chunk in enumerate(chunks[1:]):
        is_last = (i == len(chunks) - 2)
        markup = reply_markup if is_last else None
        await safe_answer(message, chunk, reply_markup=markup)
