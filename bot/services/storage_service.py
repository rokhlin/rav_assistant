import os
import re
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import aiofiles
from config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.cloud_dir = settings.cloud_path
        self.notes_dir = settings.notes_path

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Очищает имя файла от опасных символов."""
        name = re.sub(r'[\\/*?:"<>|]', "", name)
        name = name.replace(" ", "_")
        return name[:100]

    async def save_to_cloud(self, file_bytes: bytes, original_filename: str) -> Dict[str, Any]:
        """
        Сохраняет файл в папку облака с отметкой времени.
        """
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        safe_name = self._sanitize_filename(original_filename)
        final_filename = f"{timestamp}_{safe_name}"
        destination = self.cloud_dir / final_filename

        async with aiofiles.open(destination, "wb") as f:
            await f.write(file_bytes)

        file_size_kb = len(file_bytes) / 1024
        size_kb_rounded = round(file_size_kb, 2) if file_size_kb >= 0.01 else 0.01
        logger.info(f"Файл сохранен в облако: {destination} ({size_kb_rounded} KB)")

        return {
            "filename": final_filename,
            "path": str(destination),
            "size_kb": size_kb_rounded,
            "size_bytes": len(file_bytes),
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S")
        }

    async def save_note(
        self,
        title: str,
        content: str,
        note_type: str = "text",
        tags: Optional[List[str]] = None,
        raw_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создает и сохраняет заметку в формате Markdown (.md).
        """
        now = datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d %H:%M")
        file_prefix = now.strftime("%Y%m%d_%H%M%S")
        
        safe_title = self._sanitize_filename(title or "Новая_заметка")
        filename = f"{file_prefix}_{safe_title}.md"
        destination = self.notes_dir / filename

        tags_list = tags or ["заметка"]
        tags_yaml = ", ".join([f'"{t}"' for t in tags_list])

        # Формирование содержимого Markdown
        md_content = f"""---
title: "{title}"
date: "{timestamp_str}"
type: "{note_type}"
tags: [{tags_yaml}]
---

# {title}

{content.strip()}
"""
        if raw_text and raw_text.strip() != content.strip():
            md_content += f"\n\n---\n### Исходный текст / расшифровка\n> {raw_text.strip()}\n"

        async with aiofiles.open(destination, "w", encoding="utf-8") as f:
            await f.write(md_content)

        logger.info(f"Заметка сохранена: {destination}")

        return {
            "filename": filename,
            "path": str(destination),
            "title": title,
            "type": note_type,
            "tags": tags_list,
            "created_at": timestamp_str
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику по хранилищам (файлы, заметки, свободное место).
        """
        cloud_files = list(self.cloud_dir.glob("*")) if self.cloud_dir.exists() else []
        notes_files = list(self.notes_dir.glob("*.md")) if self.notes_dir.exists() else []

        # Свободное место
        try:
            total, used, free = shutil.disk_usage(self.cloud_dir)
            disk_free_gb = round(free / (1024 ** 3), 2)
            disk_total_gb = round(total / (1024 ** 3), 2)
        except Exception:
            disk_free_gb = -1
            disk_total_gb = -1

        return {
            "cloud_path": str(self.cloud_dir),
            "cloud_files_count": len(cloud_files),
            "notes_path": str(self.notes_dir),
            "notes_count": len(notes_files),
            "disk_free_gb": disk_free_gb,
            "disk_total_gb": disk_total_gb
        }

storage_service = StorageService()
