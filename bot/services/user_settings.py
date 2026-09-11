import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from config import settings
from bot.texts import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

class UserSettingsService:
    def __init__(self, config_file: Optional[Path] = None):
        if config_file is not None:
            self.file_path = Path(config_file)
        else:
            # По умолчанию в папке конфигурации
            config_dir = Path("data/config")
            config_dir.mkdir(parents=True, exist_ok=True)
            self.file_path = config_dir / "user_settings.json"
        
        self._settings: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._settings = json.load(f)
            except Exception as e:
                logger.warning(f"Не удалось прочитать {self.file_path}: {e}")
                self._settings = {}
        else:
            self._settings = {}

    def _save(self):
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек пользователей в {self.file_path}: {e}")

    def get_language(self, user_id: Optional[int]) -> str:
        """
        Возвращает выбранный пользователем язык (ru, en, he).
        По умолчанию — русский (ru).
        """
        if not user_id:
            return DEFAULT_LANGUAGE
        uid_str = str(user_id)
        user_data = self._settings.get(uid_str, {})
        lang = user_data.get("language", DEFAULT_LANGUAGE)
        if lang not in SUPPORTED_LANGUAGES:
            return DEFAULT_LANGUAGE
        return lang

    def set_language(self, user_id: int, lang: str):
        """
        Сохраняет выбранный язык пользователя.
        """
        if lang not in SUPPORTED_LANGUAGES:
            lang = DEFAULT_LANGUAGE
        uid_str = str(user_id)
        if uid_str not in self._settings:
            self._settings[uid_str] = {}
        self._settings[uid_str]["language"] = lang
        self._save()
        logger.info(f"Для user_id={user_id} установлен язык '{lang}'")

user_settings = UserSettingsService()
