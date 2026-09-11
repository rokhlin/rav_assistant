import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("data/config/.env", "/app/data/config/.env", ".env"),
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
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_FALLBACK_MODELS: str = "gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash,gemini-flash-latest,gemini-3.1-flash-lite"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_WHISPER_MODEL: str = "whisper-1"

    # Storage
    STORAGE_CLOUD_PATH: str = "data/cloud"
    STORAGE_NOTES_PATH: str = "data/notes"

    # Web UI / Status Dashboard (for ZimaOS / CasaOS)
    WEB_PORT: int = 8080
    ENABLE_WEB_STATUS: bool = True

    # Defaults
    DEFAULT_ACTION: str = "analyze"  # "analyze" or "translate"
    TARGET_LANGUAGE: str = "Russian"

    @property
    def gemini_models_chain(self) -> List[str]:
        chain: List[str] = []
        if self.GEMINI_MODEL and self.GEMINI_MODEL.strip():
            chain.append(self.GEMINI_MODEL.strip())

        fallback_str = self.GEMINI_FALLBACK_MODELS or ""
        for m in fallback_str.split(","):
            m_clean = m.strip()
            if m_clean and m_clean not in chain:
                chain.append(m_clean)

        # Fallback list of models in case of overload or unavailability
        default_chain = [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-flash-latest",
            "gemini-3.1-flash-lite",
        ]
        for m in default_chain:
            if m not in chain:
                chain.append(m)
        return chain

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
