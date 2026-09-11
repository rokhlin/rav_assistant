import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.services.ai_service import ai_service
from bot.services.storage_service import storage_service
from bot.keyboards.inline import get_media_actions_keyboard
from bot.utils.telegram_helpers import send_chunked_response, safe_edit_text, safe_reply

logger = logging.getLogger(__name__)
router = Router(name="actions_router")

@router.callback_query(F.data == "act_cancel")
async def callback_cancel(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_text(query.message, "❌ Действие отменено.")
    await query.answer("Отменено")

@router.callback_query(F.data == "act_translate")
async def callback_translate(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    content_type = data.get("last_content_type")
    
    await query.answer("Перевожу...")
    status_msg = await safe_reply(query.message, "⏳ *Выполняю перевод на русский язык...*", parse_mode="Markdown")

    try:
        result = ""
        file_bytes = bytes.fromhex(data["last_file_bytes"]) if data.get("last_file_bytes") else None
        
        if content_type == "image" and file_bytes:
            mime = data.get("last_mime_type", "image/jpeg")
            result = await ai_service.translate_image(file_bytes, mime)
        elif content_type == "pdf" and (file_bytes or data.get("last_extracted_text")):
            result = await ai_service.translate_document_multimodal(
                file_bytes=file_bytes or b"",
                mime_type="application/pdf",
                text_content=data.get("last_extracted_text")
            )
        elif data.get("last_extracted_text"):
            result = await ai_service.translate_text(data["last_extracted_text"])
        else:
            await safe_edit_text(status_msg, "⚠️ Исходные данные для перевода устарели. Пожалуйста, отправьте файл заново.")
            return

        kb = get_media_actions_keyboard(file_type=content_type or "doc", current_action="translate")
        await send_chunked_response(
            message=query.message,
            status_msg=status_msg,
            full_text=result,
            reply_markup=kb
        )

    except Exception as e:
        logger.error(f"Ошибка повторного перевода: {e}", exc_info=True)
        await safe_edit_text(status_msg, f"❌ Ошибка перевода: {e}")

@router.callback_query(F.data == "act_analyze")
async def callback_analyze(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    content_type = data.get("last_content_type")
    
    await query.answer("Анализирую...")
    status_msg = await safe_reply(query.message, "⏳ *Анализирую документ...*", parse_mode="Markdown")

    try:
        result = ""
        file_bytes = bytes.fromhex(data["last_file_bytes"]) if data.get("last_file_bytes") else None
        
        if content_type == "image" and file_bytes:
            mime = data.get("last_mime_type", "image/jpeg")
            result = await ai_service.analyze_document_image(
                image_bytes=file_bytes,
                mime_type=mime,
                custom_instruction=data.get("last_caption")
            )
        elif content_type == "pdf" and (file_bytes or data.get("last_extracted_text")):
            result = await ai_service.analyze_document_multimodal(
                file_bytes=file_bytes or b"",
                mime_type="application/pdf",
                text_content=data.get("last_extracted_text"),
                custom_instruction=data.get("last_caption")
            )
        elif data.get("last_extracted_text"):
            result = await ai_service.analyze_document_text(
                text=data["last_extracted_text"],
                custom_instruction=data.get("last_caption")
            )
        else:
            await safe_edit_text(status_msg, "⚠️ Исходные данные устарели. Пожалуйста, отправьте файл заново.")
            return

        kb = get_media_actions_keyboard(file_type=content_type or "doc", current_action="analyze")
        await send_chunked_response(
            message=query.message,
            status_msg=status_msg,
            full_text=result,
            reply_markup=kb
        )

    except Exception as e:
        logger.error(f"Ошибка повторного анализа: {e}", exc_info=True)
        await safe_edit_text(status_msg, f"❌ Ошибка анализа: {e}")

@router.callback_query(F.data == "act_save_cloud")
async def callback_save_cloud(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    file_hex = data.get("last_file_bytes")
    filename = data.get("last_filename", "document.bin")

    if not file_hex:
        await query.answer("⚠️ Файл недоступен для сохранения в кэше. Отправьте его заново с командой /save", show_alert=True)
        return

    try:
        file_bytes = bytes.fromhex(file_hex)
        saved = await storage_service.save_to_cloud(file_bytes, filename)
        await query.answer("Сохранено в облако!")
        await query.message.reply(
            f"✅ **Файл успешно сохранен в облако!**\n\n"
            f"📁 Имя: `{saved['filename']}`\n"
            f"📦 Размер: `{saved['size_kb']} KB`\n"
            f"📍 Путь: `{saved['path']}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка сохранения в облако через кнопку: {e}")
        await query.answer(f"Ошибка: {e}", show_alert=True)

@router.callback_query(F.data == "act_save_note")
async def callback_save_note(query: CallbackQuery, state: FSMContext):
    """
    Преобразует текущий результат (анализ/перевод/текст) в заметку Markdown.
    """
    message_text = query.message.text or ""
    if not message_text:
        await query.answer("Нет текста для сохранения в заметку", show_alert=True)
        return

    await query.answer("Формирую заметку...")
    try:
        structured = await ai_service.structure_note(message_text)
        saved = await storage_service.save_note(
            title=structured["title"],
            content=structured["content"],
            note_type="doc_summary",
            tags=structured.get("tags", ["документ"]),
            raw_text=message_text
        )

        tags_str = " ".join([f"#{t}" for t in saved["tags"]])
        await query.message.reply(
            f"📝 **Заметка успешно создана и сохранена!**\n\n"
            f"📁 Файл: `{saved['filename']}`\n"
            f"🏷 Теги: {tags_str}\n"
            f"📌 Заголовок: *{saved['title']}*",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка создания заметки из сообщения: {e}")
        await query.answer(f"Ошибка: {e}", show_alert=True)
