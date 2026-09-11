import time
import platform
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any
from config import settings
from bot.services.storage_service import storage_service
from bot.texts import get_text, get_target_language_name

_START_TIME = time.time()

class SystemStatusService:
    @staticmethod
    def get_status() -> Dict[str, Any]:
        uptime_seconds = int(time.time() - _START_TIME)
        uptime_str = str(timedelta(seconds=uptime_seconds))

        storage_stats = storage_service.get_stats()
        
        # Память процесса
        process = psutil.Process()
        memory_mb = round(process.memory_info().rss / (1024 * 1024), 1)

        # AI провайдер и активная модель
        if settings.AI_PROVIDER.lower() == "gemini":
            provider_info = f"Google Gemini ({settings.GEMINI_MODEL})"
            api_ready = bool(settings.GEMINI_API_KEY)
        else:
            provider_info = f"OpenAI ({settings.OPENAI_MODEL} + {settings.OPENAI_WHISPER_MODEL})"
            api_ready = bool(settings.OPENAI_API_KEY)

        return {
            "uptime": uptime_str,
            "system": f"{platform.system()} {platform.release()} ({platform.machine()})",
            "provider": provider_info,
            "api_ready": api_ready,
            "default_action": "analyze" if settings.DEFAULT_ACTION == "analyze" else "translate",
            "memory_mb": memory_mb,
            "cloud_path": storage_stats["cloud_path"],
            "cloud_files_count": storage_stats["cloud_files_count"],
            "notes_path": storage_stats["notes_path"],
            "notes_count": storage_stats["notes_count"],
            "disk_free_gb": storage_stats["disk_free_gb"],
            "disk_total_gb": storage_stats["disk_total_gb"]
        }

    @classmethod
    def format_status_message(cls, lang: str = "ru") -> str:
        s = cls.get_status()
        status_icon = get_text("status_online", lang) if s["api_ready"] else get_text("status_need_key", lang)
        
        if s["disk_free_gb"] > 0:
            disk_str = get_text("status_free_of", lang, free=s['disk_free_gb'], total=s['disk_total_gb'])
        else:
            disk_str = get_text("status_unavailable", lang)

        action_text = get_text("status_action_analyze", lang) if s["default_action"] == "analyze" else get_text("status_action_translate", lang)
        current_lang_name = get_target_language_name(lang)

        msg = (
            f"{get_text('status_title', lang)}\n\n"
            f"• **{get_text('status_state', lang)}**: {status_icon}\n"
            f"• **{get_text('status_uptime', lang)}**: `{s['uptime']}`\n"
            f"• **{get_text('status_system', lang)}**: `{s['system']}`\n"
            f"• **{get_text('status_ram', lang)}**: `{s['memory_mb']} MB`\n"
            f"• **{get_text('status_current_lang', lang)}**: `{current_lang_name}`\n\n"
            f"🤖 **{get_text('status_ai_engine', lang)}**:\n"
            f"• **{get_text('status_provider', lang)}**: {s['provider']}\n"
            f"• **{get_text('status_default_action', lang)}**: `{action_text}`\n\n"
            f"💾 **{get_text('status_storage', lang)}**:\n"
            f"• **{get_text('status_cloud_folder', lang)}**: `{s['cloud_path']}`\n"
            f"  └ {get_text('status_cloud_files', lang)}: **{s['cloud_files_count']}**\n"
            f"• **{get_text('status_notes_folder', lang)}**: `{s['notes_path']}`\n"
            f"  └ {get_text('status_notes_count', lang)}: **{s['notes_count']}**\n"
            f"• **{get_text('status_disk_free', lang)}**: {disk_str}\n"
        )
        return msg

status_service = SystemStatusService()
