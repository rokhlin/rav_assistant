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
from bot.texts import get_text, get_target_language_name, ALL_MENU_BUTTONS
from bot.utils.telegram_helpers import send_chunked_response, safe_edit_text

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
    original_filename: str = "document",
    lang: str = "ru"
):
    """
    Universal content processing (image/text/doc/pdf) based on action and language.
    """
    target_lang_name = get_target_language_name(lang)
    wait_text = (
        get_text("status_analyzing_and_translating", lang)
        if action == "analyze"
        else get_text("status_translating", lang, target_lang=target_lang_name)
    )
    status_msg = await message.answer(wait_text, parse_mode="Markdown")

    try:
        result = ""
        if content_type == "image" and image_bytes:
            if action == "analyze":
                result = await ai_service.analyze_document_image(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    custom_instruction=custom_instruction,
                    lang=lang
                )
            else:
                result = await ai_service.translate_image(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    lang=lang
                )
        elif content_type == "pdf" and (raw_file_bytes or text_content):
            if action == "analyze":
                result = await ai_service.analyze_document_multimodal(
                    file_bytes=raw_file_bytes or b"",
                    mime_type="application/pdf",
                    text_content=text_content,
                    custom_instruction=custom_instruction,
                    lang=lang
                )
            else:
                result = await ai_service.translate_document_multimodal(
                    file_bytes=raw_file_bytes or b"",
                    mime_type="application/pdf",
                    text_content=text_content,
                    lang=lang
                )
        elif content_type in ["text", "docx"] and text_content:
            if action == "analyze":
                result = await ai_service.analyze_document_text(
                    text=text_content,
                    custom_instruction=custom_instruction,
                    lang=lang
                )
            else:
                result = await ai_service.translate_text(text=text_content, lang=lang)
        else:
            await safe_edit_text(status_msg, get_text("err_cannot_extract", lang))
            return

        # Inline action buttons in selected language
        reply_kb = get_media_actions_keyboard(file_type=content_type, current_action=action, lang=lang)
        await send_chunked_response(
            message=message,
            status_msg=status_msg,
            full_text=result,
            reply_markup=reply_kb,
            lang=lang
        )

    except Exception as e:
        logger.error(f"Error processing content: {e}", exc_info=True)
        await safe_edit_text(status_msg, get_text("err_processing", lang, error=str(e)))

@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot, state: FSMContext, lang: str = "ru"):
    """
    Handle photos and images.
    Defaults to document analysis and translation in the selected language.
    """
    current_state = await state.get_state()
    custom_instruction = message.caption or None

    photo = message.photo[-1]  # Highest resolution
    file_info = await bot.get_file(photo.file_id)
    
    file_stream = io.BytesIO()
    await bot.download_file(file_info.file_path, destination=file_stream)
    image_bytes = file_stream.getvalue()

    # Cache in FSM context for action buttons
    await state.update_data(
        last_file_bytes=image_bytes.hex(),
        last_filename="photo.jpg",
        last_content_type="image",
        last_mime_type="image/jpeg",
        last_caption=custom_instruction
    )

    if current_state == BotStates.waiting_for_save:
        # Direct save mode
        saved = await storage_service.save_to_cloud(image_bytes, "photo.jpg")
        await message.answer(
            get_text("saved_photo_to_cloud", lang, filename=saved['filename'], size_kb=saved['size_kb']),
            parse_mode="Markdown"
        )
        await state.clear()
        return

    action = "translate" if current_state == BotStates.waiting_for_translate else "analyze"
    await _process_and_reply(
        message=message,
        content_type="image",
        action=action,
        custom_instruction=custom_instruction,
        image_bytes=image_bytes,
        mime_type="image/jpeg",
        original_filename="photo.jpg",
        lang=lang
    )
    if current_state:
        await state.clear()

@router.message(F.document)
async def handle_document(message: Message, bot: Bot, state: FSMContext, lang: str = "ru"):
    """
    Handle documents (PDF, DOCX, images sent as files).
    Defaults to document analysis and translation.
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

    # Save to cloud if save mode is active
    if current_state == BotStates.waiting_for_save:
        saved = await storage_service.save_to_cloud(file_bytes, filename)
        await message.answer(
            get_text("saved_doc_to_cloud", lang, filename=saved['filename'], size_kb=saved['size_kb']),
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
            if not text_extracted or not text_extracted.strip():
                logger.info("PDF has no embedded text layer (scan), routing to multimodal analysis")
                text_extracted = None
        except Exception as e:
            logger.warning(f"Failed to read PDF text layer ({e}), passing raw file directly to model")
            text_extracted = None

    elif ext in ["docx", "doc"] or "word" in mime or "officedocument" in mime:
        content_type = "docx"
        try:
            text_extracted = DocParser.extract_from_docx(file_bytes)
        except Exception as e:
            await message.answer(get_text("err_word_read", lang, error=str(e)))
            return

    elif ext in ["jpg", "jpeg", "png", "webp"] or "image" in mime:
        content_type = "image"
        image_bytes = file_bytes
    else:
        # Attempt to decode as plain text
        try:
            text_extracted = file_bytes.decode("utf-8")
            content_type = "text"
        except Exception:
            # If unknown binary file, save directly to cloud
            saved = await storage_service.save_to_cloud(file_bytes, filename)
            await message.answer(
                get_text("saved_unknown_file", lang, ext=ext, filename=saved['filename']),
                parse_mode="Markdown"
            )
            return

    # Cache data in FSM for action buttons
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
        original_filename=filename,
        lang=lang
    )
    if current_state:
        await state.clear()

@router.message(F.text, ~F.text.startswith("/"))
async def handle_plain_text(message: Message, state: FSMContext, lang: str = "ru"):
    """
    Handle plain text messages without command.
    Defaults to document analysis and translation (or pure translation if in translation state).
    """
    current_state = await state.get_state()
    text = message.text.strip()

    # Ignore menu button presses in all supported languages
    if text in ALL_MENU_BUTTONS:
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
        text_content=text,
        lang=lang
    )
    if current_state:
        await state.clear()
