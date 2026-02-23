from __future__ import annotations

import asyncio
import base64
import re
from functools import partial
from typing import Any

import httpx
import structlog
from google import genai
from google.genai.types import GenerateContentConfig

from nostr_dvm_agent.config import Settings

logger = structlog.get_logger()

DEFAULT_MODEL = "gemini-2.5-flash"
IMAGE_MODEL = "gemini-2.0-flash-exp"
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0


class GeminiClient:
    """Async wrapper around the Google GenAI SDK for Gemini inference."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model
        self._http = httpx.AsyncClient(timeout=30)

    async def close(self) -> None:
        await self._http.aclose()

    def _sync_generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model: str | None = None,
    ) -> str:
        config = GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system:
            config.system_instruction = system

        response = self._client.models.generate_content(
            model=model or self._model,
            contents=prompt,
            config=config,
        )
        return response.text or ""

    async def _generate(self, prompt: str, **kwargs: Any) -> str:
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(
                    None, partial(self._sync_generate, prompt, **kwargs)
                )
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF ** (attempt + 1)
                    logger.warning("gemini_retry", attempt=attempt + 1, wait=wait, error=str(exc))
                    await asyncio.sleep(wait)
        raise last_exc  # type: ignore[misc]

    async def generate_text(self, prompt: str, **params: Any) -> str:
        temperature = float(params.get("temperature", 0.7))
        max_tokens = int(params.get("max_tokens", 4096))

        logger.info("gemini_generate_text", prompt_len=len(prompt))
        result = await self._generate(prompt, temperature=temperature, max_tokens=max_tokens)
        logger.info("gemini_text_result", result_len=len(result))
        return result

    async def translate(self, text: str, target_language: str = "English", source_language: str = "auto") -> str:
        system = "You are a professional translator. Translate accurately while preserving meaning and tone."
        prompt = f"Translate the following text to {target_language}:\n\n{text}"
        if source_language != "auto":
            prompt = f"Translate the following text from {source_language} to {target_language}:\n\n{text}"

        logger.info("gemini_translate", target=target_language, text_len=len(text))
        return await self._generate(prompt, system=system, temperature=0.3)

    async def summarize(self, text: str, **params: Any) -> str:
        max_length = params.get("max_length", "concise")
        system = "You are an expert at creating clear, accurate summaries."
        prompt = f"Provide a {max_length} summary of the following text:\n\n{text}"

        logger.info("gemini_summarize", text_len=len(text))
        return await self._generate(prompt, system=system, temperature=0.3)

    async def generate_image(self, prompt: str, **params: Any) -> str:
        """Generate an image using Gemini's native image generation.

        Uses response_modalities=["IMAGE", "TEXT"] to request actual image
        output. Falls back to a text description if image generation is
        unavailable for the configured model.
        """
        logger.info("gemini_image", prompt_len=len(prompt))

        try:
            config = GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                temperature=0.8,
            )
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                partial(
                    self._client.models.generate_content,
                    model=IMAGE_MODEL,
                    contents=f"Generate an image: {prompt}",
                    config=config,
                ),
            )

            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    img_bytes = part.inline_data.data
                    mime = part.inline_data.mime_type or "image/png"
                    b64 = base64.b64encode(img_bytes).decode()
                    data_url = f"data:{mime};base64,{b64}"
                    logger.info("gemini_image_generated", mime=mime, size=len(img_bytes))
                    return data_url

            if response.text:
                return response.text

        except Exception:
            logger.warning("gemini_image_gen_fallback", reason="model may not support image output")

        system = "You are a creative visual artist. Create a vivid, detailed visual description."
        result = await self._generate(
            f"Create a detailed visual description for: {prompt}",
            system=system,
            temperature=0.8,
        )
        return result

    async def extract_text(self, url: str, content: str | None = None, **params: Any) -> str:
        """Analyze and extract key information from web content.

        If `content` is provided, it is used directly. Otherwise this method
        only works with content pre-fetched by the caller.
        """
        if not content:
            content = f"[URL: {url} - content was not available for extraction]"

        system = "You are an expert at analyzing and extracting key information from web content."
        prompt = (
            f"Analyze and extract the key information from the following web page content.\n"
            f"Source URL: {url}\n\n"
            f"Content:\n{content[:50000]}"
        )

        logger.info("gemini_extract", url=url, content_len=len(content))
        return await self._generate(prompt, system=system, temperature=0.2)

    def estimate_tokens(self, text: str) -> int:
        """Rough token count estimate (1 token ~ 4 chars for English)."""
        return len(text) // 4
