import io
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.states import BotStates
from bot.services.stt_service import stt_service
from bot.services.ai_service import ai_service
from bot.services.storage_service import storage_service
from bot.texts import get_text
from bot.utils.telegram_helpers import safe_edit_text

logger = logging.getLogger(__name__)
router = Router(name="notes_router")

@router.message(F.voice)
@router.message(F.audio)
async def handle_voice_message(message: Message, bot: Bot, state: FSMContext, lang: str = "ru"):
    """
    Обработка голосового сообщения / аудиофайла для создания заметки на выбранном языке.
    """
    status_msg = await message.answer(get_text("status_transcribing_note", lang), parse_mode="Markdown")
    try:
        # Скачивание аудио
        audio_obj = message.voice or message.audio
        file_info = await bot.get_file(audio_obj.file_id)
        
        file_stream = io.BytesIO()
        await bot.download_file(file_info.file_path, destination=file_stream)
        audio_bytes = file_stream.getvalue()

        # Транскрибация
        raw_text = await stt_service.transcribe(audio_bytes, mime_type="audio/ogg", lang=lang)
        if not raw_text:
            await safe_edit_text(status_msg, get_text("err_stt_failed", lang))
            return

        # AI форматирование заметки на выбранном языке
        structured = await ai_service.structure_note(raw_text, lang=lang)

        # Сохранение в .md файл
        tag_voice = get_text("tag_voice", lang)
        saved_info = await storage_service.save_note(
            title=structured["title"],
            content=structured["content"],
            note_type="voice",
            tags=structured.get("tags", [tag_voice]),
            raw_text=raw_text,
            lang=lang
        )

        tags_str = " ".join([f"#{t}" for t in saved_info["tags"]])
        response_text = get_text(
            "saved_voice_note",
            lang,
            filename=saved_info["filename"],
            tags=tags_str,
            title=saved_info["title"],
            content=structured["content"],
            orig_saved=get_text("orig_recording_saved", lang)
        )
        await safe_edit_text(status_msg, response_text, parse_mode="Markdown")
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка обработки аудио/заметки: {e}", exc_info=True)
        await safe_edit_text(status_msg, get_text("err_note_failed", lang, error=str(e)))

@router.message(BotStates.waiting_for_note, F.text)
async def handle_text_note_in_state(message: Message, state: FSMContext, lang: str = "ru"):
    """
    Обработка текста в режиме создания заметки.
    """
    status_msg = await message.answer(get_text("status_formatting_note", lang), parse_mode="Markdown")
    try:
        text = message.text.strip()
        structured = await ai_service.structure_note(text, lang=lang)

        tag_text = get_text("tag_text", lang)
        saved_info = await storage_service.save_note(
            title=structured["title"],
            content=structured["content"],
            note_type="text",
            tags=structured.get("tags", [tag_text]),
            raw_text=text,
            lang=lang
        )

        tags_str = " ".join([f"#{t}" for t in saved_info["tags"]])
        response_text = get_text(
            "saved_text_note",
            lang,
            filename=saved_info["filename"],
            tags=tags_str,
            title=saved_info["title"],
            content=structured["content"]
        )
        await safe_edit_text(status_msg, response_text, parse_mode="Markdown")
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка создания текстовой заметки: {e}", exc_info=True)
        await safe_edit_text(status_msg, get_text("err_note_failed", lang, error=str(e)))
