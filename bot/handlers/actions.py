import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.services.ai_service import ai_service
from bot.services.storage_service import storage_service
from bot.services.user_settings import user_settings
from bot.keyboards.inline import get_media_actions_keyboard, get_language_keyboard
from bot.keyboards.reply import get_main_menu_keyboard
from bot.texts import get_text, get_target_language_name, SUPPORTED_LANGUAGES
from bot.utils.telegram_helpers import send_chunked_response, safe_edit_text, safe_reply

logger = logging.getLogger(__name__)
router = Router(name="actions_router")

@router.callback_query(F.data == "act_cancel")
async def callback_cancel(query: CallbackQuery, state: FSMContext, lang: str = "ru"):
    await state.clear()
    await safe_edit_text(query.message, get_text("action_canceled", lang))
    await query.answer(get_text("toast_canceled", lang))

@router.callback_query(F.data.startswith("lang_set:"))
async def callback_set_language(query: CallbackQuery, lang: str = "ru"):
    new_lang = query.data.split(":")[1]
    if new_lang not in SUPPORTED_LANGUAGES:
        await query.answer()
        return

    user_id = query.from_user.id
    user_settings.set_language(user_id, new_lang)
    lang_name = SUPPORTED_LANGUAGES[new_lang]

    # Update inline language selection keyboard (mark newly selected language)
    try:
        await safe_edit_text(
            query.message,
            get_text("lang_select_prompt", new_lang),
            reply_markup=get_language_keyboard(new_lang),
            parse_mode="Markdown"
        )
    except Exception:
        pass

    await query.answer(f"✓ {lang_name}")

    # Send confirmation and update persistent bottom menu in new language
    confirm_text = get_text("lang_switched", new_lang, lang_name=lang_name)
    await query.message.answer(
        confirm_text,
        reply_markup=get_main_menu_keyboard(new_lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "act_translate")
async def callback_translate(query: CallbackQuery, state: FSMContext, lang: str = "ru"):
    data = await state.get_data()
    content_type = data.get("last_content_type")
    
    target_lang_name = get_target_language_name(lang)
    await query.answer(get_text("toast_translating", lang))
    status_msg = await safe_reply(
        query.message,
        get_text("status_translating", lang, target_lang=target_lang_name),
        parse_mode="Markdown"
    )

    try:
        result = ""
        file_bytes = bytes.fromhex(data["last_file_bytes"]) if data.get("last_file_bytes") else None
        
        if content_type == "image" and file_bytes:
            mime = data.get("last_mime_type", "image/jpeg")
            result = await ai_service.translate_image(file_bytes, mime, lang=lang)
        elif content_type == "pdf" and (file_bytes or data.get("last_extracted_text")):
            result = await ai_service.translate_document_multimodal(
                file_bytes=file_bytes or b"",
                mime_type="application/pdf",
                text_content=data.get("last_extracted_text"),
                lang=lang
            )
        elif data.get("last_extracted_text"):
            result = await ai_service.translate_text(data["last_extracted_text"], lang=lang)
        else:
            await safe_edit_text(status_msg, get_text("err_data_expired", lang))
            return

        kb = get_media_actions_keyboard(file_type=content_type or "doc", current_action="translate", lang=lang)
        await send_chunked_response(
            message=query.message,
            status_msg=status_msg,
            full_text=result,
            reply_markup=kb,
            lang=lang
        )

    except Exception as e:
        logger.error(f"Error during re-translation: {e}", exc_info=True)
        await safe_edit_text(status_msg, get_text("err_translation", lang, error=str(e)))

@router.callback_query(F.data == "act_analyze")
async def callback_analyze(query: CallbackQuery, state: FSMContext, lang: str = "ru"):
    data = await state.get_data()
    content_type = data.get("last_content_type")
    
    await query.answer(get_text("toast_analyzing", lang))
    status_msg = await safe_reply(
        query.message,
        get_text("status_analyzing", lang),
        parse_mode="Markdown"
    )

    try:
        result = ""
        file_bytes = bytes.fromhex(data["last_file_bytes"]) if data.get("last_file_bytes") else None
        
        if content_type == "image" and file_bytes:
            mime = data.get("last_mime_type", "image/jpeg")
            result = await ai_service.analyze_document_image(
                image_bytes=file_bytes,
                mime_type=mime,
                custom_instruction=data.get("last_caption"),
                lang=lang
            )
        elif content_type == "pdf" and (file_bytes or data.get("last_extracted_text")):
            result = await ai_service.analyze_document_multimodal(
                file_bytes=file_bytes or b"",
                mime_type="application/pdf",
                text_content=data.get("last_extracted_text"),
                custom_instruction=data.get("last_caption"),
                lang=lang
            )
        elif data.get("last_extracted_text"):
            result = await ai_service.analyze_document_text(
                text=data["last_extracted_text"],
                custom_instruction=data.get("last_caption"),
                lang=lang
            )
        else:
            await safe_edit_text(status_msg, get_text("err_data_expired_analyze", lang))
            return

        kb = get_media_actions_keyboard(file_type=content_type or "doc", current_action="analyze", lang=lang)
        await send_chunked_response(
            message=query.message,
            status_msg=status_msg,
            full_text=result,
            reply_markup=kb,
            lang=lang
        )

    except Exception as e:
        logger.error(f"Error during re-analysis: {e}", exc_info=True)
        await safe_edit_text(status_msg, get_text("err_analysis", lang, error=str(e)))

@router.callback_query(F.data == "act_save_cloud")
async def callback_save_cloud(query: CallbackQuery, state: FSMContext, lang: str = "ru"):
    data = await state.get_data()
    file_hex = data.get("last_file_bytes")
    filename = data.get("last_filename", "document.bin")

    if not file_hex:
        await query.answer(get_text("err_save_cache_missing", lang), show_alert=True)
        return

    try:
        file_bytes = bytes.fromhex(file_hex)
        saved = await storage_service.save_to_cloud(file_bytes, filename)
        await query.answer("OK")
        msg_text = get_text(
            "saved_to_cloud",
            lang,
            filename=saved["filename"],
            size_kb=saved["size_kb"],
            path=saved["path"]
        )
        await query.message.reply(msg_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error saving to cloud via button: {e}")
        await query.answer(f"Error: {e}", show_alert=True)

@router.callback_query(F.data == "act_save_note")
async def callback_save_note(query: CallbackQuery, state: FSMContext, lang: str = "ru"):
    message_text = query.message.text or ""
    if not message_text:
        await query.answer(get_text("err_no_text_for_note", lang), show_alert=True)
        return

    await query.answer(get_text("toast_forming_note", lang))
    try:
        structured = await ai_service.structure_note(message_text, lang=lang)
        tag_doc = get_text("tag_doc", lang)
        saved = await storage_service.save_note(
            title=structured["title"],
            content=structured["content"],
            note_type="doc_summary",
            tags=structured.get("tags", [tag_doc]),
            raw_text=message_text,
            lang=lang
        )

        tags_str = " ".join([f"#{t}" for t in saved["tags"]])
        msg_text = get_text(
            "saved_note_from_msg",
            lang,
            filename=saved["filename"],
            tags=tags_str,
            title=saved["title"]
        )
        await query.message.reply(msg_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error creating note from message: {e}")
        await query.answer(f"Error: {e}", show_alert=True)
