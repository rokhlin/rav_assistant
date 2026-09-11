import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("data/config/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    ALLOWED_USER_IDS: str = ""

    # AI Provider: "gemini" or "openai"
    AI_PROVIDER: str = "gemini"

    # Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_WHISPER_MODEL: str = "whisper-1"

    # Storage
    STORAGE_CLOUD_PATH: str = "data/cloud"
    STORAGE_NOTES_PATH: str = "data/notes"

    # Defaults
    DEFAULT_ACTION: str = "analyze"  # "analyze" (Анализ и перевод) or "translate"
    TARGET_LANGUAGE: str = "Русский"

    @property
    def allowed_users(self) -> List[int]:
        if not self.ALLOWED_USER_IDS.strip():
            return []
        users = []
        for uid in self.ALLOWED_USER_IDS.split(","):
            uid_clean = uid.strip()
            if uid_clean.isdigit():
                users.append(int(uid_clean))
        return users

    @property
    def cloud_path(self) -> Path:
        p = Path(self.STORAGE_CLOUD_PATH)
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        return p

    @property
    def notes_path(self) -> Path:
        p = Path(self.STORAGE_NOTES_PATH)
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        return p

settings = Settings()
