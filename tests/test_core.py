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




