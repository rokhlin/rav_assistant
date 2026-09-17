"""
Unified localization and text loading module for the bot.
Loads interface messages, buttons, commands, and AI prompts from translations.json.
"""

import json
from pathlib import Path
from typing import Dict, Any, Set

_TRANSLATIONS_FILE = Path(__file__).parent / "translations.json"

with open(_TRANSLATIONS_FILE, "r", encoding="utf-8") as _f:
    _data = json.load(_f)

SUPPORTED_LANGUAGES: Dict[str, str] = _data.get("supported_languages", {})
DEFAULT_LANGUAGE: str = _data.get("default_language", "ru")
TARGET_LANGUAGE_NAMES: Dict[str, str] = _data.get("target_language_names", {})
TEXTS: Dict[str, Dict[str, str]] = _data.get("texts", {})


def get_text(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """
    Returns localized string by key for the specified language.
    If the key is missing in the chosen language, falls back to the default language.
    """
    selected_lang = lang if lang in TEXTS else DEFAULT_LANGUAGE
    template = TEXTS.get(selected_lang, {}).get(key)
    if template is None:
        template = TEXTS.get(DEFAULT_LANGUAGE, {}).get(key, f"[{key}]")
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


def get_target_language_name(lang: str = DEFAULT_LANGUAGE) -> str:
    """Returns human-readable name of the target language for AI prompts."""
    return TARGET_LANGUAGE_NAMES.get(lang, "Russian")


# Button text sets across all languages for handler filtering
BUTTON_ANALYZE_ALL: Set[str] = {TEXTS[l]["btn_analyze"] for l in TEXTS if "btn_analyze" in TEXTS[l]}
BUTTON_TRANSLATE_ALL: Set[str] = {TEXTS[l]["btn_translate"] for l in TEXTS if "btn_translate" in TEXTS[l]}
BUTTON_SCAN_ALL: Set[str] = {TEXTS[l]["btn_scan"] for l in TEXTS if "btn_scan" in TEXTS[l]}
BUTTON_NOTE_ALL: Set[str] = {TEXTS[l]["btn_note"] for l in TEXTS if "btn_note" in TEXTS[l]}
BUTTON_SAVE_ALL: Set[str] = {TEXTS[l]["btn_save"] for l in TEXTS if "btn_save" in TEXTS[l]}
BUTTON_STATUS_ALL: Set[str] = {TEXTS[l]["btn_status"] for l in TEXTS if "btn_status" in TEXTS[l]}
BUTTON_HELP_ALL: Set[str] = {TEXTS[l]["btn_help"] for l in TEXTS if "btn_help" in TEXTS[l]}
BUTTON_LANG_ALL: Set[str] = {TEXTS[l]["btn_language"] for l in TEXTS if "btn_language" in TEXTS[l]}

ALL_MENU_BUTTONS: Set[str] = (
    BUTTON_ANALYZE_ALL
    | BUTTON_TRANSLATE_ALL
    | BUTTON_SCAN_ALL
    | BUTTON_NOTE_ALL
    | BUTTON_SAVE_ALL
    | BUTTON_STATUS_ALL
    | BUTTON_HELP_ALL
    | BUTTON_LANG_ALL
)
