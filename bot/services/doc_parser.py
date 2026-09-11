import io
import logging
from typing import Tuple, Optional
from pypdf import PdfReader
from docx import Document
from PIL import Image

logger = logging.getLogger(__name__)

class DocParser:
    @staticmethod
    def extract_from_pdf(file_bytes: bytes) -> Tuple[str, int]:
        """
        Извлекает текст из PDF документа.
        Возвращает (текст, количество_страниц).
        """
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            num_pages = len(reader.pages)
            text_parts = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(f"--- Страница {i+1} ---\n{page_text}")
            
            full_text = "\n\n".join(text_parts).strip()
            return full_text, num_pages
        except Exception as e:
            logger.error(f"Ошибка парсинга PDF: {e}")
            raise RuntimeError(f"Не удалось прочитать PDF: {e}")

    @staticmethod
    def extract_from_docx(file_bytes: bytes) -> str:
        """
        Извлекает текст, заголовки и таблицы из Word (.docx) документа.
        """
        try:
            doc = Document(io.BytesIO(file_bytes))
            paragraphs = []
            for p in doc.paragraphs:
                if p.text.strip():
                    paragraphs.append(p.text)

            # Извлечение данных из таблиц
            for t_idx, table in enumerate(doc.tables):
                table_lines = [f"\n[Таблица {t_idx+1}]"]
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells]
                    table_lines.append(" | ".join(row_cells))
                paragraphs.append("\n".join(table_lines))

            return "\n\n".join(paragraphs).strip()
        except Exception as e:
            logger.error(f"Ошибка парсинга DOCX: {e}")
            raise RuntimeError(f"Не удалось прочитать DOCX: {e}")

    @staticmethod
    def validate_image(file_bytes: bytes) -> Tuple[bool, Optional[str], Optional[Tuple[int, int]]]:
        """
        Проверяет корректность изображения, возвращает (is_valid, format, dimensions).
        """
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                return True, img.format, img.size
        except Exception as e:
            logger.warning(f"Ошибка валидации изображения: {e}")
            return False, None, None
