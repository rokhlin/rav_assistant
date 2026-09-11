import io
import logging
import asyncio
from config import settings
from bot.services.ai_service import ai_service
from bot.texts import get_text

logger = logging.getLogger(__name__)

class STTService:
    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()

    async def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/ogg", lang: str = "ru") -> str:
        """
        Транскрибирует аудиозапись в текст.
        Поддерживает Google Gemini Audio и OpenAI Whisper.
        """
        if self.provider == "gemini" and ai_service.gemini_client:
            from google.genai import types
            prompt = get_text("ai_prompt_transcribe", lang)
            contents = [
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                prompt
            ]
            try:
                text = await ai_service._call_gemini_with_fallback(contents)
                return text.strip()
            except Exception as e:
                logger.error(f"Gemini Audio Transcription error: {e}")
                raise RuntimeError(f"Ошибка транскрибации Gemini: {e}")

        elif ai_service.openai_client:
            try:
                audio_file = io.BytesIO(audio_bytes)
                audio_file.name = "voice.ogg" if "ogg" in mime_type else "voice.mp3"
                transcript = await ai_service.openai_client.audio.transcriptions.create(
                    model=settings.OPENAI_WHISPER_MODEL,
                    file=audio_file
                )
                return transcript.text.strip()
            except Exception as e:
                logger.error(f"OpenAI Whisper error: {e}")
                raise RuntimeError(f"Ошибка транскрибации Whisper: {e}")

        else:
            raise RuntimeError("Не настроен AI провайдер для распознавания речи (STT)!")

stt_service = STTService()
