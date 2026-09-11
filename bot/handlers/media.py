import io
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.states import BotStates
from bot.services.doc_parser import DocParser
from bot.services.ai_service import ai_service
from bot.services.storage_service import storage_service
from bot.keyboards.inline import get_media_actions_keyboard

logger = logging.getLogger(__name__)
router = Router(name="media_router")

async def _process_and_reply(
    message: Message,
    content_type: str,
    action: str,
    custom_instruction: str = None,
    text_content: str = None,
    image_bytes: bytes = None,
    mime_type: str = "image/jpeg",
    raw_file_bytes: bytes = None,
    original_filename: str = "document"
):
    """
    Универсальная обработка контента (изображение/текст/документ)
    в зависимости от выбранного действия (analyze или translate).
    """
    status_msg = await message.answer(
        "⏳ *Анализирую и перевожу документ...*" if action == "analyze" else "⏳ *Перевожу на русский язык...*",
        parse_mode="Markdown"
    )

    try:
        result = ""
        if content_type == "image" and image_bytes:
            if action == "analyze":
                result = await ai_service.analyze_document_image(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    custom_instruction=custom_instruction
                )
            else:
                result = await ai_service.translate_image(
                    image_bytes=image_bytes,
                    mime_type=mime_type
                )
        elif content_type in ["text", "pdf", "docx"] and text_content:
            if action == "analyze":
                result = await ai_service.analyze_document_text(
                    text=text_content,
                    custom_instruction=custom_instruction
                )
            else:
                result = await ai_service.translate_text(text=text_content)
        else:
            await status_msg.edit_text("❌ Не удалось извлечь содержимое для обработки.")
            return

        # Инлайн-кнопки под ответом
        reply_kb = get_media_actions_keyboard(file_type=content_type, current_action=action)
        
        # Если текст очень длинный (> 4096 символов для Telegram), разбиваем
        if len(result) <= 4000:
            await status_msg.edit_text(result, reply_markup=reply_kb, parse_mode="Markdown")
        else:
            chunks = [result[i:i+3800] for i in range(0, len(result), 3800)]
            await status_msg.edit_text(chunks[0], parse_mode="Markdown")
            for chunk in chunks[1:-1]:
                await message.answer(chunk, parse_mode="Markdown")
            await message.answer(chunks[-1], reply_markup=reply_kb, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка при обработке контента: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Произошла ошибка при обработке: {e}")

@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot, state: FSMContext):
    """
    Обработка фотографий и изображений.
    По умолчанию (если ничего не выбрано) выполняется 'Анализ и перевод'.
    """
    current_state = await state.get_state()
    custom_instruction = message.caption or None

    photo = message.photo[-1]  # Берем максимальное разрешение
    file_info = await bot.get_file(photo.file_id)
    
    file_stream = io.BytesIO()
    await bot.download_file(file_info.file_path, destination=file_stream)
    image_bytes = file_stream.getvalue()

    # Сохраняем в FSM контекст на случай нажатия кнопок под сообщением
    await state.update_data(
        last_file_bytes=image_bytes.hex(),
        last_filename="photo.jpg",
        last_content_type="image",
        last_mime_type="image/jpeg",
        last_caption=custom_instruction
    )

    if current_state == BotStates.waiting_for_save:
        # Режим сохранения
        saved = await storage_service.save_to_cloud(image_bytes, "photo.jpg")
        await message.answer(
            f"✅ **Фотография сохранена в облако!**\n\n"
            f"📁 Имя файла: `{saved['filename']}`\n"
            f"📦 Размер: `{saved['size_kb']} KB`",
            parse_mode="Markdown"
        )
        await state.clear()
        return

    # Определение действия: если translate — переводим, иначе по умолчанию ANALYZE
    action = "translate" if current_state == BotStates.waiting_for_translate else "analyze"
    await _process_and_reply(
        message=message,
        content_type="image",
        action=action,
        custom_instruction=custom_instruction,
        image_bytes=image_bytes,
        mime_type="image/jpeg",
        original_filename="photo.jpg"
    )
    if current_state:
        await state.clear()

@router.message(F.document)
async def handle_document(message: Message, bot: Bot, state: FSMContext):
    """
    Обработка документов (PDF, DOCX, изображения как файлы).
    По умолчанию выполняется 'Анализ и перевод'.
    """
    current_state = await state.get_state()
    doc = message.document
    filename = doc.file_name or "document"
    mime = doc.mime_type or ""
    custom_instruction = message.caption or None

    file_info = await bot.get_file(doc.file_id)
    file_stream = io.BytesIO()
    await bot.download_file(file_info.file_path, destination=file_stream)
    file_bytes = file_stream.getvalue()

    # Сохранение в облако, если активен режим сохранения
    if current_state == BotStates.waiting_for_save:
        saved = await storage_service.save_to_cloud(file_bytes, filename)
        await message.answer(
            f"✅ **Документ сохранен в облако!**\n\n"
            f"📁 Имя файла: `{saved['filename']}`\n"
            f"📦 Размер: `{saved['size_kb']} KB`",
            parse_mode="Markdown"
        )
        await state.clear()
        return

    ext = filename.lower().split(".")[-1] if "." in filename else ""
    action = "translate" if current_state == BotStates.waiting_for_translate else "analyze"

    text_extracted = None
    content_type = "doc"
    image_bytes = None

    if ext == "pdf" or "pdf" in mime:
        content_type = "pdf"
        try:
            text_extracted, pages = DocParser.extract_from_pdf(file_bytes)
            if not text_extracted.strip():
                # Если PDF без текста (скан), уведомляем
                await message.answer("⚠️ Текстовый слой в PDF не найден (возможно, отсканированный документ). Попробуйте отправить страницу как фото.")
                return
        except Exception as e:
            await message.answer(f"❌ Ошибка чтения PDF: {e}")
            return

    elif ext in ["docx", "doc"] or "word" in mime or "officedocument" in mime:
        content_type = "docx"
        try:
            text_extracted = DocParser.extract_from_docx(file_bytes)
        except Exception as e:
            await message.answer(f"❌ Ошибка чтения Word-документа: {e}")
            return

    elif ext in ["jpg", "jpeg", "png", "webp"] or "image" in mime:
        content_type = "image"
        image_bytes = file_bytes
    else:
        # Попытка прочитать как текст
        try:
            text_extracted = file_bytes.decode("utf-8")
            content_type = "text"
        except Exception:
            # Если неизвестный бинарный файл — предлагаем сохранить в облако
            saved = await storage_service.save_to_cloud(file_bytes, filename)
            await message.answer(
                f"📎 Файл формата `.{ext}` сохранен в хранилище:\n`{saved['filename']}`",
                parse_mode="Markdown"
            )
            return

    # Кэшируем данные в FSM для кнопок
    await state.update_data(
        last_file_bytes=file_bytes.hex() if len(file_bytes) < 15 * 1024 * 1024 else None,
        last_filename=filename,
        last_content_type=content_type,
        last_extracted_text=text_extracted,
        last_caption=custom_instruction
    )

    await _process_and_reply(
        message=message,
        content_type=content_type,
        action=action,
        custom_instruction=custom_instruction,
        text_content=text_extracted,
        image_bytes=image_bytes,
        mime_type=mime or "image/jpeg",
        raw_file_bytes=file_bytes,
        original_filename=filename
    )
    if current_state:
        await state.clear()

@router.message(F.text, ~F.text.startswith("/"))
async def handle_plain_text(message: Message, state: FSMContext):
    """
    Обработка обычного текстового сообщения без команды.
    По умолчанию выполняется 'Анализ и перевод' (или 'Перевод' если активен режим перевода).
    """
    current_state = await state.get_state()
    text = message.text.strip()

    # Игнорируем нажатия на кнопки меню (они обрабатываются в commands.py)
    if text in ["🔍 Анализ и перевод", "🌐 Перевод", "📝 Новая заметка", "💾 Сохранить в облако", "📊 Статус бота", "ℹ️ Справка"]:
        return

    action = "translate" if current_state == BotStates.waiting_for_translate else "analyze"

    await state.update_data(
        last_extracted_text=text,
        last_content_type="text",
        last_filename="text_message.txt"
    )

    await _process_and_reply(
        message=message,
        content_type="text",
        action=action,
        text_content=text
    )
    if current_state:
        await state.clear()
