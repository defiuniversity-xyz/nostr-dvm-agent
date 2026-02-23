from __future__ import annotations

import asyncio
from functools import partial
from typing import Any

import structlog
from google import genai
from google.genai.types import GenerateContentConfig

from nostr_dvm_agent.config import Settings

logger = structlog.get_logger()

DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiClient:
    """Async wrapper around the Google GenAI SDK for Gemini inference."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def _sync_generate(self, prompt: str, *, system: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> str:
        config = GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system:
            config.system_instruction = system

        response = self._client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
            config=config,
        )
        return response.text or ""

    async def _generate(self, prompt: str, **kwargs: Any) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self._sync_generate, prompt, **kwargs))

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
        """
        Generate an image description or use Gemini's image capabilities.

        Note: Gemini's native image generation may require specific model versions.
        This returns a detailed description that could be fed to an image model,
        or uses Gemini's vision capabilities if available.
        """
        system = "You are a creative visual artist. Describe the image in vivid detail."
        enhanced_prompt = f"Create a detailed visual description for: {prompt}"

        logger.info("gemini_image", prompt_len=len(prompt))
        return await self._generate(enhanced_prompt, system=system, temperature=0.8)

    async def extract_text(self, url: str, **params: Any) -> str:
        system = "You are an expert at analyzing and extracting key information from web content."
        prompt = f"Analyze and extract the key information from this URL: {url}\n\nProvide a structured extraction of the main content."

        logger.info("gemini_extract", url=url)
        return await self._generate(prompt, system=system, temperature=0.2)

    def estimate_tokens(self, text: str) -> int:
        """Rough token count estimate (1 token ~ 4 chars for English)."""
        return len(text) // 4
