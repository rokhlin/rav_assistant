import json
import logging
from typing import Dict, Any, Optional, List
from config import settings
from bot.texts import get_text, get_target_language_name

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()
        self._init_client()

    def _init_client(self):
        self.gemini_client = None
        self.openai_client = None

        if self.provider == "gemini" or settings.GEMINI_API_KEY:
            try:
                from google import genai
                if settings.GEMINI_API_KEY:
                    self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                    logger.info("Инициализирован Google GenAI Client")
            except Exception as e:
                logger.warning(f"Ошибка инициализации Gemini client: {e}")

        if self.provider == "openai" or settings.OPENAI_API_KEY:
            try:
                from openai import AsyncOpenAI
                if settings.OPENAI_API_KEY:
                    self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                    logger.info("Инициализирован AsyncOpenAI Client")
            except Exception as e:
                logger.warning(f"Ошибка инициализации OpenAI client: {e}")

    async def translate_text(self, text: str, target_lang: Optional[str] = None, lang: str = "ru") -> str:
        if not target_lang:
            target_lang = get_target_language_name(lang)
        prompt = get_text("ai_prompt_translate_text", lang, target_lang=target_lang, text=text)
        return await self._generate_text(prompt)

    async def analyze_document_text(self, text: str, custom_instruction: Optional[str] = None, lang: str = "ru") -> str:
        prompt = get_text("ai_prompt_analyze_text", lang)
        if custom_instruction:
            prompt += get_text("ai_custom_instruction", lang, instruction=custom_instruction)
        prompt += f"\n{text}"

        return await self._generate_text(prompt)

    async def translate_image(self, image_bytes: bytes, mime_type: str = "image/jpeg", target_lang: Optional[str] = None, lang: str = "ru") -> str:
        if not target_lang:
            target_lang = get_target_language_name(lang)
        prompt = get_text("ai_prompt_translate_image", lang, target_lang=target_lang)
        return await self._generate_vision(prompt, image_bytes, mime_type)

    async def analyze_document_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        custom_instruction: Optional[str] = None,
        lang: str = "ru"
    ) -> str:
        prompt = get_text("ai_prompt_analyze_image", lang)
        if custom_instruction:
            prompt += get_text("ai_custom_instruction", lang, instruction=custom_instruction)

        return await self._generate_vision(prompt, image_bytes, mime_type)

    async def analyze_document_multimodal(
        self,
        file_bytes: bytes,
        mime_type: str = "application/pdf",
        text_content: Optional[str] = None,
        custom_instruction: Optional[str] = None,
        lang: str = "ru"
    ) -> str:
        prompt = get_text("ai_prompt_analyze_multimodal", lang)
        if custom_instruction:
            prompt += get_text("ai_custom_instruction", lang, instruction=custom_instruction)

        # Если провайдер Gemini - передаем PDF напрямую (поддерживает сканы, таблицы и изображения)
        if (self.provider == "gemini" or self.gemini_client) and mime_type == "application/pdf":
            return await self._generate_vision(prompt, file_bytes, mime_type)

        # Если есть извлеченный текст - анализируем текст
        if text_content and text_content.strip():
            return await self._generate_text(prompt + f"\n{text_content}")

        # Если OpenAI и это PDF без текста (скан) - извлекаем изображения страниц
        if mime_type == "application/pdf":
            from bot.services.doc_parser import DocParser
            images = DocParser.extract_images_from_pdf(file_bytes)
            if images:
                return await self._generate_vision(prompt, images[0], "image/jpeg")

        err_msg = get_text("err_cannot_extract", lang)
        raise RuntimeError(err_msg)

    async def translate_document_multimodal(
        self,
        file_bytes: bytes,
        mime_type: str = "application/pdf",
        text_content: Optional[str] = None,
        target_lang: Optional[str] = None,
        lang: str = "ru"
    ) -> str:
        if not target_lang:
            target_lang = get_target_language_name(lang)
        prompt = get_text("ai_prompt_translate_multimodal", lang, target_lang=target_lang)

        if (self.provider == "gemini" or self.gemini_client) and mime_type == "application/pdf":
            return await self._generate_vision(prompt, file_bytes, mime_type)

        if text_content and text_content.strip():
            return await self._generate_text(prompt + f"\n\n{text_content}")

        if mime_type == "application/pdf":
            from bot.services.doc_parser import DocParser
            images = DocParser.extract_images_from_pdf(file_bytes)
            if images:
                return await self._generate_vision(prompt, images[0], "image/jpeg")

        err_msg = get_text("err_cannot_extract", lang)
        raise RuntimeError(err_msg)

    async def structure_note(self, raw_text: str, lang: str = "ru") -> Dict[str, Any]:
        """
        Преобразует сырой текст или транскрипцию голоса в структурированную заметку.
        """
        prompt = get_text("ai_prompt_structure_note", lang, raw_text=raw_text)

        response_text = await self._generate_text(prompt)
        default_title = get_text("default_note_title", lang)
        default_tag = get_text("tag_note", lang)
        try:
            # Очистка markdown разметки ```json ... ``` если вернулась
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()

            data = json.loads(cleaned)
            return {
                "title": data.get("title", default_title),
                "tags": data.get("tags", [default_tag]),
                "content": data.get("content", raw_text)
            }
        except Exception as e:
            logger.warning(f"Не удалось распарсить JSON заметки ({e}), используем базовый шаблон")
            first_line = raw_text.strip().split("\n")[0][:40]
            return {
                "title": first_line or default_title,
                "tags": [default_tag],
                "content": raw_text
            }

    async def _call_gemini_with_fallback(self, contents: Any) -> str:
        """
        Выполняет вызов Gemini API с поддержкой каскадного fallback на младшие / альтернативные версии моделей.
        Если выбранная модель перегружена (503 Service Unavailable), возвращает ошибку квоты или недоступна,
        запрос автоматически повторяется для следующих моделей из fallback цепочки.
        """
        import asyncio
        loop = asyncio.get_running_loop()
        models = settings.gemini_models_chain
        last_error = None

        for idx, model in enumerate(models):
            try:
                def _invoke(m=model):
                    return self.gemini_client.models.generate_content(
                        model=m,
                        contents=contents
                    )

                response = await loop.run_in_executor(None, _invoke)
                if idx > 0:
                    logger.warning(
                        f"Основная модель недоступна. Запрос успешно выполнен с fallback-моделью: '{model}'"
                    )
                return response.text or ""
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Ошибка Gemini API при вызове модели '{model}': {e}. "
                    f"({'Пробуем следующую модель...' if idx < len(models) - 1 else 'Все fallback-модели исчерпаны.'})"
                )
                continue

        logger.error(f"Все модели Gemini из fallback-цепочки {models} завершились ошибкой. Последняя ошибка: {last_error}")
        raise last_error

    async def _generate_text(self, prompt: str) -> str:
        if self.provider == "gemini" and self.gemini_client:
            try:
                return await self._call_gemini_with_fallback(prompt)
            except Exception as e:
                logger.error(f"Gemini API error after fallback attempts: {e}")
                raise

        elif self.openai_client:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content or ""
        else:
            raise RuntimeError("Не настроен API ключ для AI провайдера (Gemini или OpenAI)!")

    async def _generate_vision(self, prompt: str, image_bytes: bytes, mime_type: str) -> str:
        if self.provider == "gemini" and self.gemini_client:
            from google.genai import types
            contents = [
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt
            ]
            try:
                return await self._call_gemini_with_fallback(contents)
            except Exception as e:
                logger.error(f"Gemini Vision API error after fallback attempts: {e}")
                raise

        elif self.openai_client:
            import base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2500
            )
            return response.choices[0].message.content or ""
        else:
            raise RuntimeError("Не настроен API ключ для работы с изображениями (Gemini или OpenAI)!")

ai_service = AIService()
