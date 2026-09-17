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
                    logger.info("Initialized Google GenAI Client")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

        if self.provider == "openai" or settings.OPENAI_API_KEY:
            try:
                from openai import AsyncOpenAI
                if settings.OPENAI_API_KEY:
                    self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                    logger.info("Initialized AsyncOpenAI Client")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")

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

        # Gemini supports PDF directly (scans, tables, and images)
        if (self.provider == "gemini" or self.gemini_client) and mime_type == "application/pdf":
            return await self._generate_vision(prompt, file_bytes, mime_type)

        # If extracted text is available, analyze text
        if text_content and text_content.strip():
            return await self._generate_text(prompt + f"\n{text_content}")

        # For OpenAI with scanned PDF, extract page images
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

    async def analyze_document_images_batch(
        self,
        images_bytes: List[bytes],
        mime_types: Optional[List[str]] = None,
        custom_instruction: Optional[str] = None,
        action: str = "analyze",
        lang: str = "ru"
    ) -> str:
        """
        Analyze or translate multiple photos/images (album/batch) simultaneously.
        Merges sequence of pages, deduplicates overlapping fragments, and produces
        a unified document analysis and translation.
        """
        target_lang = get_target_language_name(lang)
        count = len(images_bytes)
        if not mime_types:
            mime_types = ["image/jpeg"] * count

        if action == "translate":
            prompt = get_text("ai_prompt_translate_album", lang, count=count, target_lang=target_lang)
        else:
            prompt = get_text("ai_prompt_analyze_album", lang, count=count, target_lang=target_lang)

        if custom_instruction:
            prompt += get_text("ai_custom_instruction", lang, instruction=custom_instruction)

        if (self.provider == "gemini" or self.gemini_client):
            from google.genai import types
            parts = [
                types.Part.from_bytes(data=img, mime_type=mime)
                for img, mime in zip(images_bytes, mime_types)
            ]
            parts.append(prompt)
            return await self._call_gemini_with_fallback(parts)

        elif self.openai_client:
            import base64
            content_items: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
            for img, mime in zip(images_bytes, mime_types):
                b64 = base64.b64encode(img).decode("utf-8")
                content_items.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"}
                })
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": content_items}]
            )
            return response.choices[0].message.content or ""
        else:
            raise RuntimeError("No API key configured for AI provider!")

    async def structure_note(self, raw_text: str, lang: str = "ru") -> Dict[str, Any]:
        """
        Convert raw text or voice transcript into structured note.
        Understands formatting instructions (shopping lists, tables, checklists)
        and extracts pure content without leaking meta-instructions or prompts.
        """
        prompt = get_text("ai_prompt_structure_note", lang, raw_text=raw_text)

        response_text = await self._generate_text(prompt)
        default_title = get_text("default_note_title", lang)
        default_tag = get_text("tag_note", lang)
        try:
            import re
            cleaned = response_text.strip()
            # Extract JSON block between ```json ... ``` or ``` ... ```
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()
            else:
                if not cleaned.startswith("{"):
                    s = cleaned.find("{")
                    e = cleaned.rfind("}")
                    if s != -1 and e != -1:
                        cleaned = cleaned[s:e + 1].strip()

            data = json.loads(cleaned)
            content = data.get("content", "").strip()
            title = data.get("title", default_title).strip()
            tags = data.get("tags", [default_tag])
            if not content:
                content = raw_text.strip()

            # Guard against model returning generic refusal placeholders
            content_lower = content.lower()
            if any(refusal in content_lower for refusal in [
                "текст не предоставлен",
                "текст отсутствует",
                "исходный текст не предоставлен",
                "пожалуйста, укажите содержимое",
                "no content provided",
                "no text provided"
            ]):
                content = raw_text.strip()
                title = raw_text.strip().split("\n")[0][:40]

            return {
                "title": title or default_title,
                "tags": tags if isinstance(tags, list) and tags else [default_tag],
                "content": content
            }
        except Exception as e:
            logger.warning(f"Failed to parse note JSON ({e}), using default template")
            first_line = raw_text.strip().split("\n")[0][:40]
            return {
                "title": first_line or default_title,
                "tags": [default_tag],
                "content": raw_text.strip()
            }

    async def _call_gemini_with_fallback(self, contents: Any) -> str:
        """
        Execute Gemini API call with cascading fallback to secondary models.
        If primary model is overloaded (503), quota-limited, or unavailable,
        request retries automatically with subsequent models from fallback chain.
        """
        import asyncio
        import time
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

                logger.info(f"Starting Gemini API request. Model: '{model}'")
                start_time = time.time()
                response = await loop.run_in_executor(None, _invoke)
                elapsed_time = time.time() - start_time
                logger.info(f"Gemini API request succeeded. Model: '{model}', Elapsed time: {elapsed_time:.2f} seconds")
                
                if idx > 0:
                    logger.warning(
                        f"Primary model unavailable. Request succeeded with fallback model: '{model}'"
                    )
                return response.text or ""
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Gemini API error calling model '{model}': {e}. "
                    f"({'Trying next fallback model...' if idx < len(models) - 1 else 'All fallback models exhausted.'})"
                )
                continue

        logger.error(f"All Gemini models in fallback chain {models} failed. Last error: {last_error}")
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
            raise RuntimeError("No API key configured for AI provider (Gemini or OpenAI)!")

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
            raise RuntimeError("No API key configured for vision processing (Gemini or OpenAI)!")

ai_service = AIService()
