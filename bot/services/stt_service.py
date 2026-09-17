import io
import logging
from config import settings
from bot.services.ai_service import ai_service
from bot.texts import get_text

logger = logging.getLogger(__name__)

class STTService:
    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()

    async def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/ogg", lang: str = "ru") -> str:
        """
        Transcribe audio recording to text.
        Supports Google Gemini Audio and OpenAI Whisper.
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
                cleaned_text = text.strip()
                if prompt in cleaned_text:
                    cleaned_text = cleaned_text.replace(prompt, "").strip()
                for prefix in [
                    "Вот транскрипция голосового сообщения:",
                    "Вот транскрипция:",
                    "Транскрипция:",
                    "Транскрипция голосового сообщения:",
                    "Here is the transcription:",
                    "Transcription:"
                ]:
                    if cleaned_text.lower().startswith(prefix.lower()):
                        cleaned_text = cleaned_text[len(prefix):].strip()
                return cleaned_text
            except Exception as e:
                logger.error(f"Gemini Audio Transcription error: {e}")
                raise RuntimeError(f"Gemini transcription error: {e}")

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
                raise RuntimeError(f"Whisper transcription error: {e}")

        else:
            raise RuntimeError("No AI provider configured for speech recognition (STT)!")

stt_service = STTService()
