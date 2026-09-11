import time
import platform
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any
from config import settings
from bot.services.storage_service import storage_service

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
            "default_action": "Анализ и перевод" if settings.DEFAULT_ACTION == "analyze" else "Перевод",
            "memory_mb": memory_mb,
            "cloud_path": storage_stats["cloud_path"],
            "cloud_files_count": storage_stats["cloud_files_count"],
            "notes_path": storage_stats["notes_path"],
            "notes_count": storage_stats["notes_count"],
            "disk_free_gb": storage_stats["disk_free_gb"],
            "disk_total_gb": storage_stats["disk_total_gb"]
        }

    @classmethod
    def format_status_message(cls) -> str:
        s = cls.get_status()
        status_icon = "🟢 В сети" if s["api_ready"] else "🟡 Требуется API ключ"
        
        disk_str = f"{s['disk_free_gb']} GB свободно из {s['disk_total_gb']} GB" if s["disk_free_gb"] > 0 else "Недоступно"

        msg = (
            f"📊 **Статус бота и системы**\n\n"
            f"• **Состояние**: {status_icon}\n"
            f"• **Время работы (Uptime)**: `{s['uptime']}`\n"
            f"• **Система**: `{s['system']}`\n"
            f"• **Потребление RAM**: `{s['memory_mb']} MB`\n\n"
            f"🤖 **AI Движок**:\n"
            f"• **Провайдер**: {s['provider']}\n"
            f"• **Действие по умолчанию**: `{s['default_action']}`\n\n"
            f"💾 **Хранилище (ZimaOS)**:\n"
            f"• **Папка Облака**: `{s['cloud_path']}`\n"
            f"  └ Сохранено файлов: **{s['cloud_files_count']}**\n"
            f"• **Папка Заметок**: `{s['notes_path']}`\n"
            f"  └ Создано заметок (.md): **{s['notes_count']}**\n"
            f"• **Свободное место на диске**: {disk_str}\n"
        )
        return msg

status_service = SystemStatusService()
