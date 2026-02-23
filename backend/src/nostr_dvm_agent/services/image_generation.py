from __future__ import annotations

from typing import Any

from nostr_dvm_agent.ai.gemini_client import GeminiClient
from nostr_dvm_agent.core.event_handler import get_primary_input_text
from nostr_dvm_agent.services.base import BaseDVMService


class ImageGenerationService(BaseDVMService):
    kind = 5100
    name = "Image Generation"
    description = "Text-to-image generation powered by Gemini"
    default_cost_msats = 2000

    def __init__(self, gemini: GeminiClient, cost_msats: int = 2000) -> None:
        self._gemini = gemini
        self.default_cost_msats = cost_msats

    async def validate_input(self, job_data: dict[str, Any]) -> bool:
        text = get_primary_input_text(job_data)
        return len(text.strip()) > 0

    async def estimate_cost(self, job_data: dict[str, Any]) -> int:
        return self.default_cost_msats

    async def execute(self, job_data: dict[str, Any]) -> str:
        prompt = get_primary_input_text(job_data)
        params = job_data.get("params", {})
        return await self._gemini.generate_image(prompt, **params)
