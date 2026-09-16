import re
import uuid
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import aiofiles
from config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, cloud_dir: Optional[Path] = None, notes_dir: Optional[Path] = None):
        self.cloud_dir = Path(cloud_dir) if cloud_dir is not None else settings.cloud_path
        self.notes_dir = Path(notes_dir) if notes_dir is not None else settings.notes_path
        # In-memory cache for recent notes to enable short callback_data tokens
        self._note_cache: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize filename from unsafe characters."""
        name = re.sub(r'[\\/*?:"<>|]', "", name)
        name = name.replace(" ", "_")
        return name[:100]

    async def save_to_cloud(
        self,
        file_bytes: bytes,
        original_filename: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Save file to cloud directory with timestamp prefix.
        If user_id is provided, saves to data/cloud/<user_id>/
        """
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        safe_name = self._sanitize_filename(original_filename)
        final_filename = f"{timestamp}_{safe_name}"

        target_dir = self.cloud_dir / str(user_id) if user_id else self.cloud_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / final_filename

        async with aiofiles.open(destination, "wb") as f:
            await f.write(file_bytes)

        file_size_kb = len(file_bytes) / 1024
        size_kb_rounded = round(file_size_kb, 2) if file_size_kb >= 0.01 else 0.01
        logger.info(f"File saved to cloud: {destination} ({size_kb_rounded} KB)")

        return {
            "filename": final_filename,
            "path": str(destination),
            "size_kb": size_kb_rounded,
            "size_bytes": len(file_bytes),
            "user_id": user_id,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S")
        }

    async def save_note(
        self,
        title: str,
        content: str,
        note_type: str = "text",
        tags: Optional[List[str]] = None,
        raw_text: Optional[str] = None,
        lang: str = "ru",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create and save note in Markdown format (.md).
        If user_id is provided, saves to data/notes/<user_id>/
        """
        from bot.texts import get_text
        now = datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d %H:%M")
        file_prefix = now.strftime("%Y%m%d_%H%M%S")
        
        default_title = get_text("default_note_title", lang)
        safe_title = self._sanitize_filename(title or default_title)
        filename = f"{file_prefix}_{safe_title}.md"

        target_dir = self.notes_dir / str(user_id) if user_id else self.notes_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / filename

        default_tag = get_text("tag_note", lang)
        tags_list = tags or [default_tag]
        tags_yaml = ", ".join([f'"{t}"' for t in tags_list])

        author_meta = f'\nauthor_id: "{user_id}"' if user_id else ""

        # Format Markdown content
        md_content = f"""---
title: "{title}"
date: "{timestamp_str}"
type: "{note_type}"{author_meta}
tags: [{tags_yaml}]
---

# {title}

{content.strip()}
"""
        if raw_text and raw_text.strip() != content.strip():
            header = get_text("orig_text_header", lang)
            md_content += f"\n\n---\n### {header}\n> {raw_text.strip()}\n"

        async with aiofiles.open(destination, "w", encoding="utf-8") as f:
            await f.write(md_content)

        logger.info(f"Note saved: {destination}")

        token = uuid.uuid4().hex[:10]
        note_info = {
            "token": token,
            "filename": filename,
            "path": str(destination),
            "title": title,
            "content": content.strip(),
            "type": note_type,
            "tags": tags_list,
            "raw_text": raw_text,
            "user_id": user_id,
            "created_at": timestamp_str
        }

        # Cache in memory (keep last 200 notes)
        if len(self._note_cache) > 200:
            oldest_key = next(iter(self._note_cache))
            del self._note_cache[oldest_key]
        self._note_cache[token] = note_info

        return note_info

    def get_note_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached note info by its token."""
        return self._note_cache.get(token)

    async def share_note(
        self,
        token_or_path: Union[str, Path],
        sender_id: int,
        recipient_id: int,
        sender_name: str,
        recipient_name: str,
        lang: str = "ru"
    ) -> Dict[str, Any]:
        """
        Copy note to shared directory (data/notes/shared/from_<sender_name>_<filename>)
        with metadata about author and recipient.
        """
        cached_info = None
        source_path = None

        if isinstance(token_or_path, str) and token_or_path in self._note_cache:
            cached_info = self._note_cache[token_or_path]
            source_path = Path(cached_info["path"])
        else:
            source_path = Path(token_or_path)

        orig_filename = source_path.name if source_path else "note.md"
        safe_sender = self._sanitize_filename(sender_name or f"user_{sender_id}")
        shared_filename = f"from_{safe_sender}_{orig_filename}"

        shared_dir = self.notes_dir / "shared"
        shared_dir.mkdir(parents=True, exist_ok=True)
        shared_destination = shared_dir / shared_filename

        now = datetime.now()
        shared_date_str = now.strftime("%Y-%m-%d %H:%M")

        title = cached_info.get("title", "") if cached_info else "Note"
        content = cached_info.get("content", "") if cached_info else ""
        tags_list = cached_info.get("tags", []) if cached_info else []
        note_type = cached_info.get("type", "text") if cached_info else "text"
        raw_text = cached_info.get("raw_text") if cached_info else None

        # If not in cache or if source file exists, read directly
        if source_path and source_path.exists():
            async with aiofiles.open(source_path, "r", encoding="utf-8") as f:
                existing_text = await f.read()
        else:
            existing_text = ""

        tags_yaml = ", ".join([f'"{t}"' for t in tags_list])
        meta_block = f"""---
title: "{title}"
date: "{shared_date_str}"
type: "{note_type}"
author: "{sender_name}"
author_id: "{sender_id}"
shared_to: "{recipient_name}"
shared_to_id: "{recipient_id}"
tags: [{tags_yaml}]
---
"""
        if existing_text and existing_text.startswith("---"):
            # Replace YAML header in existing note with enriched shared header
            parts = existing_text.split("---", 2)
            if len(parts) >= 3:
                body = parts[2]
                shared_content = meta_block + body.lstrip()
            else:
                shared_content = meta_block + "\n\n" + existing_text
        elif existing_text:
            shared_content = meta_block + "\n\n" + existing_text
        else:
            shared_content = f"{meta_block}\n# {title}\n\n{content}\n"
            if raw_text and raw_text.strip() != content.strip():
                shared_content += f"\n\n---\n> {raw_text.strip()}\n"

        async with aiofiles.open(shared_destination, "w", encoding="utf-8") as f:
            await f.write(shared_content)

        logger.info(f"Note shared and saved to: {shared_destination}")

        return {
            "filename": shared_filename,
            "path": str(shared_destination),
            "title": title,
            "content": content,
            "tags": tags_list,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "sender_name": sender_name,
            "recipient_name": recipient_name,
            "shared_at": shared_date_str
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Return storage statistics (files, notes, free disk space).
        Recursively counts files in all user subdirectories and shared folder.
        """
        cloud_files = [f for f in self.cloud_dir.rglob("*") if f.is_file()] if self.cloud_dir.exists() else []
        notes_files = [f for f in self.notes_dir.rglob("*.md") if f.is_file()] if self.notes_dir.exists() else []

        # Free disk space
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
