import io
import os
import pytest
import asyncio
from pathlib import Path
from docx import Document
from pypdf import PdfWriter
from PIL import Image
from bot.services.doc_parser import DocParser
from bot.services.storage_service import StorageService
from bot.services.system_status import SystemStatusService

@pytest.mark.asyncio
async def test_storage_service(tmp_path):
    # Настраиваем временные пути
    cloud_dir = tmp_path / "cloud"
    notes_dir = tmp_path / "notes"
    cloud_dir.mkdir(parents=True, exist_ok=True)
    notes_dir.mkdir(parents=True, exist_ok=True)
    service = StorageService(cloud_dir=cloud_dir, notes_dir=notes_dir)

    # 1. Тест сохранения в облако
    dummy_data = b"Hello Cloud Storage!"
    res_cloud = await service.save_to_cloud(dummy_data, "test_file.txt")
    assert Path(res_cloud["path"]).exists()
    assert res_cloud["size_kb"] > 0
    assert "test_file.txt" in res_cloud["filename"]

    # 2. Тест создания заметки .md
    res_note = await service.save_note(
        title="Оплата счета за интернет",
        content="## Задачи\n- [ ] Оплатить до 15 числа\n- [ ] Сумма: 500 руб",
        note_type="voice",
        tags=["счета", "интернет"],
        raw_text="Надо оплатить интернет до пятнадцатого пятьсот рублей"
    )
    note_path = Path(res_note["path"])
    assert note_path.exists()
    assert note_path.suffix == ".md"
    
    # Проверка содержимого .md
    content = note_path.read_text(encoding="utf-8")
    assert 'title: "Оплата счета за интернет"' in content
    assert 'tags: ["счета", "интернет"]' in content
    assert "- [ ] Оплатить до 15 числа" in content
    assert "Исходный текст / расшифровка" in content

def test_docx_parser():
    # Создаем тестовый .docx в памяти
    doc = Document()
    doc.add_heading("Договор аренды", level=1)
    doc.add_paragraph("Арендатор обязуется внести оплату в размере 50 000 руб.")
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Услуга"
    table.rows[0].cells[1].text = "Стоимость"
    table.rows[1].cells[0].text = "Аренда"
    table.rows[1].cells[1].text = "50000"

    bio = io.BytesIO()
    doc.save(bio)
    file_bytes = bio.getvalue()

    extracted = DocParser.extract_from_docx(file_bytes)
    assert "Договор аренды" in extracted
    assert "50 000 руб." in extracted
    assert "Услуга | Стоимость" in extracted

def test_image_validation():
    img = Image.new("RGB", (100, 100), color="blue")
    bio = io.BytesIO()
    img.save(bio, format="JPEG")
    img_bytes = bio.getvalue()

    is_valid, fmt, size = DocParser.validate_image(img_bytes)
    assert is_valid is True
    assert fmt == "JPEG"
    assert size == (100, 100)

def test_pdf_parser():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    bio = io.BytesIO()
    writer.write(bio)
    file_bytes = bio.getvalue()

    text, pages = DocParser.extract_from_pdf(file_bytes)
    assert pages == 1
    assert isinstance(text, str)

def test_system_status():
    status_msg = SystemStatusService.format_status_message()
    assert "Статус бота и системы" in status_msg
    assert "AI Движок" in status_msg
    assert "Хранилище" in status_msg

def test_config_env_path(tmp_path):
    config_dir = tmp_path / "data" / "config"
    config_dir.mkdir(parents=True)
    env_file = config_dir / ".env"
    env_file.write_text("DEFAULT_ACTION=translate\nTARGET_LANGUAGE=Немецкий\n", encoding="utf-8")

    from config import Settings
    custom_settings = Settings(_env_file=str(env_file))
    assert custom_settings.DEFAULT_ACTION == "translate"
    assert custom_settings.TARGET_LANGUAGE == "Немецкий"

@pytest.mark.asyncio
async def test_web_server_endpoints():
    from bot.services.web_server import handle_dashboard, handle_health
    from aiohttp import web
    
    # Dashboard HTML
    req = web.Request
    resp_dashboard = await handle_dashboard(None)
    assert resp_dashboard.status == 200
    assert resp_dashboard.content_type == "text/html"
    assert "Telegram Helper Bot" in resp_dashboard.text

    # Health JSON
    resp_health = await handle_health(None)
    assert resp_health.status == 200
    assert resp_health.content_type == "application/json"

def test_telegram_helpers_split_text():
    from bot.utils.telegram_helpers import split_text
    # Small text
    assert split_text("Hello") == ["Hello"]

    # Long text with paragraphs
    paragraphs = ["Paragraph " + str(i) * 100 for i in range(50)]
    long_text = "\n\n".join(paragraphs)
    chunks = split_text(long_text, max_chunk_size=500)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 500

@pytest.mark.asyncio
async def test_safe_edit_text_fallback():
    from unittest.mock import AsyncMock
    from aiogram.exceptions import TelegramBadRequest
    from bot.utils.telegram_helpers import safe_edit_text

    mock_msg = AsyncMock()
    # First call with Markdown raises "can't parse entities"
    # Second call with parse_mode=None succeeds
    mock_msg.edit_text.side_effect = [
        TelegramBadRequest(method=AsyncMock(), message="Bad Request: can't parse entities: unclosed entity"),
        AsyncMock(text="plain text response")
    ]

    res = await safe_edit_text(mock_msg, "Some text with _unclosed entity", parse_mode="Markdown")
    assert mock_msg.edit_text.call_count == 2
    # Verify second call had parse_mode=None
    assert mock_msg.edit_text.call_args_list[1].kwargs["parse_mode"] is None

def test_pdf_extract_images():
    from bot.services.doc_parser import DocParser
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    bio = io.BytesIO()
    writer.write(bio)
    file_bytes = bio.getvalue()

    images = DocParser.extract_images_from_pdf(file_bytes)
    assert isinstance(images, list)

def test_localization_texts_complete():
    from bot.texts import TEXTS, SUPPORTED_LANGUAGES, get_text, get_target_language_name, ALL_MENU_BUTTONS
    
    assert set(SUPPORTED_LANGUAGES.keys()) == {"ru", "en", "he"}
    
    # Check that keys are consistent across languages
    ru_keys = set(TEXTS["ru"].keys())
    en_keys = set(TEXTS["en"].keys())
    he_keys = set(TEXTS["he"].keys())

    assert ru_keys == en_keys, f"Missing in EN: {ru_keys - en_keys}"
    assert ru_keys == he_keys, f"Missing in HE: {ru_keys - he_keys}"

    # Check get_text helper and fallback
    assert get_text("btn_translate", "ru") == "🌐 Перевод"
    assert get_text("btn_translate", "en") == "🌐 Translation"
    assert get_text("btn_translate", "he") == "🌐 תרגום"
    assert get_text("btn_translate", "unknown_lang") == "🌐 Перевод"

    # Check formatting
    assert "Alice" in get_text("welcome", "ru", name="Alice")
    assert "Alice" in get_text("welcome", "en", name="Alice")
    assert "Alice" in get_text("welcome", "he", name="Alice")

    # Target language names
    assert get_target_language_name("ru") == "Русский"
    assert get_target_language_name("en") == "English"
    assert get_target_language_name("he") == "עברית"

    # Button sets
    assert "🌐 Перевод" in ALL_MENU_BUTTONS
    assert "🌐 Translation" in ALL_MENU_BUTTONS
    assert "🌐 תרגום" in ALL_MENU_BUTTONS

def test_user_settings_persistence(tmp_path):
    from bot.services.user_settings import UserSettingsService

    config_file = tmp_path / "user_settings.json"
    service = UserSettingsService(config_file=config_file)

    # Default is 'ru' without asking
    assert service.get_language(12345) == "ru"
    assert service.get_language(None) == "ru"

    # Change to english
    service.set_language(12345, "en")
    assert service.get_language(12345) == "en"

    # Change to hebrew
    service.set_language(67890, "he")
    assert service.get_language(67890) == "he"

    # Reload from disk
    service2 = UserSettingsService(config_file=config_file)
    assert service2.get_language(12345) == "en"
    assert service2.get_language(67890) == "he"
    assert service2.get_language(99999) == "ru"

    # Invalid language falls back to 'ru'
    service.set_language(12345, "invalid_lang")
    assert service.get_language(12345) == "ru"

def test_localized_keyboards():
    from bot.keyboards.reply import get_main_menu_keyboard
    from bot.keyboards.inline import get_cancel_keyboard, get_media_actions_keyboard, get_language_keyboard

    # Reply keyboard buttons
    kb_ru = get_main_menu_keyboard("ru")
    assert any("Анализ и перевод" in btn.text for row in kb_ru.keyboard for btn in row)
    assert any("Язык" in btn.text for row in kb_ru.keyboard for btn in row)

    kb_en = get_main_menu_keyboard("en")
    assert any("Analyze & Translate" in btn.text for row in kb_en.keyboard for btn in row)
    assert any("Language" in btn.text for row in kb_en.keyboard for btn in row)

    kb_he = get_main_menu_keyboard("he")
    assert any("ניתוח ותרגום" in btn.text for row in kb_he.keyboard for btn in row)
    assert any("שפה" in btn.text for row in kb_he.keyboard for btn in row)

    # Cancel keyboard
    assert "Отмена" in get_cancel_keyboard("ru").inline_keyboard[0][0].text
    assert "Cancel" in get_cancel_keyboard("en").inline_keyboard[0][0].text
    assert "ביטול" in get_cancel_keyboard("he").inline_keyboard[0][0].text

    # Language selection keyboard
    lang_kb = get_language_keyboard("en")
    buttons_flat = [b for row in lang_kb.inline_keyboard for b in row]
    callbacks = [b.callback_data for b in buttons_flat]
    assert "lang_set:ru" in callbacks
    assert "lang_set:en" in callbacks
    assert "lang_set:he" in callbacks
    # English should have checkmark
    en_btn = next(b for b in buttons_flat if b.callback_data == "lang_set:en")
    assert "✓" in en_btn.text

def test_system_status_multilingual():
    from bot.services.system_status import SystemStatusService

    msg_ru = SystemStatusService.format_status_message(lang="ru")
    assert "Статус бота и системы" in msg_ru
    assert "Русский" in msg_ru

    msg_en = SystemStatusService.format_status_message(lang="en")
    assert "Bot & System Status" in msg_en
    assert "English" in msg_en

    msg_he = SystemStatusService.format_status_message(lang="he")
    assert "סטטוס בוט ומערכת" in msg_he
    assert "עברית" in msg_he

@pytest.mark.asyncio
async def test_ai_service_prompts_multilingual(monkeypatch):
    from bot.services.ai_service import AIService
    
    captured_prompts = []
    async def fake_generate_text(prompt: str) -> str:
        captured_prompts.append(prompt)
        return '{"title": "Test Title", "tags": ["tag"], "content": "Content"}'

    service = AIService()
    monkeypatch.setattr(service, "_generate_text", fake_generate_text)

    # 1. Translate in Russian (default)
    await service.translate_text("Hello world", lang="ru")
    assert "Русский" in captured_prompts[-1]
    assert "Hello world" in captured_prompts[-1]

    # 2. Translate in English
    await service.translate_text("Привет мир", lang="en")
    assert "English" in captured_prompts[-1]
    assert "Привет мир" in captured_prompts[-1]

    # 3. Translate in Hebrew
    await service.translate_text("Hello world", lang="he")
    assert "עברית" in captured_prompts[-1]
    assert "Hello world" in captured_prompts[-1]

    # 4. Document Analysis in Russian
    await service.analyze_document_text("Счет на оплату", lang="ru")
    assert "Тип документа" in captured_prompts[-1]

    # 5. Document Analysis in English
    await service.analyze_document_text("Invoice 123", lang="en")
    assert "Document Type" in captured_prompts[-1]

    # 6. Document Analysis in Hebrew
    await service.analyze_document_text("חשבונית 123", lang="he")
    assert "סוג המסמך" in captured_prompts[-1]






