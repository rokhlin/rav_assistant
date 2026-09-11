import io
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.states import BotStates
from bot.services.stt_service import stt_service
from bot.services.ai_service import ai_service
from bot.services.storage_service import storage_service

logger = logging.getLogger(__name__)
router = Router(name="notes_router")

@router.message(F.voice)
@router.message(F.audio)
async def handle_voice_message(message: Message, bot: Bot, state: FSMContext):
    """
    Обработка голосового сообщения / аудиофайла для создания заметки.
    """
    status_msg = await message.answer("🎙 *Распознаю речь и форматирую заметку...*", parse_mode="Markdown")
    try:
        # Скачивание аудио
        audio_obj = message.voice or message.audio
        file_info = await bot.get_file(audio_obj.file_id)
        
        file_stream = io.BytesIO()
        await bot.download_file(file_info.file_path, destination=file_stream)
        audio_bytes = file_stream.getvalue()

        # Транскрибация
        raw_text = await stt_service.transcribe(audio_bytes, mime_type="audio/ogg")
        if not raw_text:
            await status_msg.edit_text("❌ Не удалось распознать речь в сообщении.")
            return

        # AI форматирование заметки
        structured = await ai_service.structure_note(raw_text)

        # Сохранение в .md файл
        saved_info = await storage_service.save_note(
            title=structured["title"],
            content=structured["content"],
            note_type="voice",
            tags=structured.get("tags", ["голос"]),
            raw_text=raw_text
        )

        tags_str = " ".join([f"#{t}" for t in saved_info["tags"]])
        response_text = (
            f"✅ **Голосовая заметка сохранена!**\n\n"
            f"📁 **Файл**: `{saved_info['filename']}`\n"
            f"🏷 **Теги**: {tags_str}\n\n"
            f"### {saved_info['title']}\n\n"
            f"{structured['content']}\n\n"
            f"_(Исходная запись сохранена в Markdown)_"
        )
        await status_msg.edit_text(response_text, parse_mode="Markdown")
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка обработки аудио/заметки: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Ошибка при создании заметки: {e}")

@router.message(BotStates.waiting_for_note, F.text)
async def handle_text_note_in_state(message: Message, state: FSMContext):
    """
    Обработка текста в режиме создания заметки.
    """
    status_msg = await message.answer("✍️ *Форматирую и сохраняю заметку...*", parse_mode="Markdown")
    try:
        text = message.text.strip()
        structured = await ai_service.structure_note(text)

        saved_info = await storage_service.save_note(
            title=structured["title"],
            content=structured["content"],
            note_type="text",
            tags=structured.get("tags", ["текст"]),
            raw_text=text
        )

        tags_str = " ".join([f"#{t}" for t in saved_info["tags"]])
        response_text = (
            f"✅ **Заметка сохранена!**\n\n"
            f"📁 **Файл**: `{saved_info['filename']}`\n"
            f"🏷 **Теги**: {tags_str}\n\n"
            f"### {saved_info['title']}\n\n"
            f"{structured['content']}"
        )
        await status_msg.edit_text(response_text, parse_mode="Markdown")
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка создания текстовой заметки: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Ошибка при создании заметки: {e}")
