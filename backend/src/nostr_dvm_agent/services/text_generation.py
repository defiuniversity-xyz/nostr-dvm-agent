from __future__ import annotations

from typing import Any

from nostr_dvm_agent.ai.gemini_client import GeminiClient
from nostr_dvm_agent.core.event_handler import get_primary_input_text
from nostr_dvm_agent.services.base import BaseDVMService


class TextGenerationService(BaseDVMService):
    kind = 5001
    name = "Text Generation"
    description = "LLM text generation powered by Gemini 3 Pro"
    default_cost_msats = 500

    def __init__(self, gemini: GeminiClient, cost_msats: int = 500) -> None:
        self._gemini = gemini
        self.default_cost_msats = cost_msats

    async def validate_input(self, job_data: dict[str, Any]) -> bool:
        text = get_primary_input_text(job_data)
        return len(text.strip()) > 0

    async def estimate_cost(self, job_data: dict[str, Any]) -> int:
        text = get_primary_input_text(job_data)
        tokens = self._gemini.estimate_tokens(text)
        if tokens > 2000:
            return self.default_cost_msats * 3
        if tokens > 500:
            return self.default_cost_msats * 2
        return self.default_cost_msats

    async def execute(self, job_data: dict[str, Any]) -> str:
        prompt = get_primary_input_text(job_data)
        params = job_data.get("params", {})
        return await self._gemini.generate_text(prompt, **params)
