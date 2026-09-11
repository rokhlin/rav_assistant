import json
import logging
from typing import Dict, Any, Optional, List
from config import settings

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

    async def translate_text(self, text: str, target_lang: str = "Русский") -> str:
        prompt = (
            f"Вы — профессиональный переводчик. Переведите следующий текст на {target_lang}. "
            "Сохраняйте исходное форматирование, структуру, списки и числовые значения. "
            "Выводите только перевод без вводных фраз.\n\n"
            f"Текст:\n{text}"
        )
        return await self._generate_text(prompt)

    async def analyze_document_text(self, text: str, custom_instruction: Optional[str] = None) -> str:
        prompt = (
            "Вы — персональный ассистент по анализу документов. "
            "Внимательно изучите текст документа и предоставьте структурированный разбор на русском языке:\n\n"
            "📋 **Тип документа**: (определите, что это: квитанция, счет, договор, штраф, уведомление от банка/госорганов и т.д.)\n"
            "🎯 **Краткая суть**: (основное содержание, отправитель, даты, ключевые условия или суммы)\n"
            "⚠️ **Что требуется от вас**: (четкие действия пользователя: оплатить до определенной даты, подписать, отправить ответ или просто ознакомиться)\n"
            "🌐 **Перевод ключевых положений**: (переведите на русский язык самое главное содержание или весь текст, если он короткий)\n\n"
        )
        if custom_instruction:
            prompt += f"Дополнительная инструкция пользователя: {custom_instruction}\n\n"
        prompt += f"Текст документа:\n{text}"

        return await self._generate_text(prompt)

    async def translate_image(self, image_bytes: bytes, mime_type: str = "image/jpeg", target_lang: str = "Русский") -> str:
        prompt = (
            f"Распознайте весь текст на этом изображении и переведите его на {target_lang}. "
            "Сохраняйте исходное логическое форматирование и числовые значения. "
            "Выдайте только готовый перевод без лишних префиксов."
        )
        return await self._generate_vision(prompt, image_bytes, mime_type)

    async def analyze_document_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        custom_instruction: Optional[str] = None
    ) -> str:
        prompt = (
            "Вы — персональный ассистент по анализу документов и изображений. "
            "Внимательно изучите документ на картинке и предоставьте структурированный ответ на русском языке:\n\n"
            "📋 **Тип документа**: (квитанция, счет, контракт, официальное письмо, выписка и т.д.)\n"
            "🎯 **Краткая суть**: (от кого, о чем, важные даты, суммы, реквизиты)\n"
            "⚠️ **Что требуется от вас**: (конкретные действия: оплатить до срока, прислать документы, явиться, либо просто сохранить для архива)\n"
            "🌐 **Перевод ключевых положений**: (перевод главного содержания документа на русский язык)\n\n"
        )
        if custom_instruction:
            prompt += f"Дополнительное указание от пользователя: {custom_instruction}\n\n"

        return await self._generate_vision(prompt, image_bytes, mime_type)

    async def structure_note(self, raw_text: str) -> Dict[str, Any]:
        """
        Преобразует сырой текст или транскрипцию голоса в структурированную заметку.
        """
        prompt = (
            "Преобразуйте следующий текст/транскрипцию в аккуратную заметку. "
            "Сформулируйте емкий заголовок (3-6 слов), подберите 1-3 релевантных тега (например: работа, покупки, идея, личное), "
            "и структурируйте содержание с помощью Markdown (списки, пункты действий - [ ], важные мысли).\n"
            "Верните ответ ИСКЛЮЧИТЕЛЬНО в формате JSON:\n"
            "{\n"
            '  "title": "Заголовок заметки",\n'
            '  "tags": ["тег1", "тег2"],\n'
            '  "content": "Структурированный Markdown текст заметки"\n'
            "}\n\n"
            f"Исходный текст:\n{raw_text}"
        )

        response_text = await self._generate_text(prompt)
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
                "title": data.get("title", "Новая заметка"),
                "tags": data.get("tags", ["заметка"]),
                "content": data.get("content", raw_text)
            }
        except Exception as e:
            logger.warning(f"Не удалось распарсить JSON заметки ({e}), используем базовый шаблон")
            first_line = raw_text.strip().split("\n")[0][:40]
            return {
                "title": first_line or "Новая заметка",
                "tags": ["заметка"],
                "content": raw_text
            }

    async def _generate_text(self, prompt: str) -> str:
        if self.provider == "gemini" and self.gemini_client:
            import asyncio
            try:
                # google-genai Client.models.generate_content is synchronous or can be run in executor
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.gemini_client.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=prompt
                    )
                )
                return response.text or ""
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
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
        import asyncio
        if self.provider == "gemini" and self.gemini_client:
            from google.genai import types
            loop = asyncio.get_running_loop()
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: self.gemini_client.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=[
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                            prompt
                        ]
                    )
                )
                return response.text or ""
            except Exception as e:
                logger.error(f"Gemini Vision API error: {e}")
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
