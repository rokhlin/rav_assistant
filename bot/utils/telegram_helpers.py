import logging
from typing import List, Optional
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

def split_text(text: str, max_chunk_size: int = 3800) -> List[str]:
    """
    Разбивает длинный текст на части по границам абзацев или строк,
    чтобы не разрывать форматирование и предложения.
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
        line_len = len(line) + 1  # учитываем перенос строки
        if current_len + line_len > max_chunk_size and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_len = 0

        # Если одна строка превышает max_chunk_size
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
    Безопасное редактирование сообщения.
    При ошибке парсинга Markdown автоматически отправляет как обычный текст без сбоя.
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
    Безопасная отправка ответа на сообщение.
    При ошибке парсинга Markdown автоматически отправляет как обычный текст.
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
    Безопасная отправка reply на сообщение.
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
    reply_markup: Optional[InlineKeyboardMarkup] = None
):
    """
    Разбивает длинный ответ нейросети на части и отправляет пользователю,
    гарантируя устойчивость к ошибкам парсинга разметки Telegram.
    """
    chunks = split_text(full_text, max_chunk_size=3800)
    if not chunks:
        await safe_edit_text(status_msg, "❌ Пустой результат ответа нейросети.", reply_markup=reply_markup)
        return

    # Первую часть редактируем в текущем сообщении статуса
    first_markup = reply_markup if len(chunks) == 1 else None
    await safe_edit_text(status_msg, chunks[0], reply_markup=first_markup)

    # Все последующие части отправляем новыми сообщениями
    for i, chunk in enumerate(chunks[1:]):
        is_last = (i == len(chunks) - 2)
        markup = reply_markup if is_last else None
        await safe_answer(message, chunk, reply_markup=markup)
