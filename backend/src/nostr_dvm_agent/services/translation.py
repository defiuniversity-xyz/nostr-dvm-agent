from __future__ import annotations

from typing import Any

from nostr_dvm_agent.ai.gemini_client import GeminiClient
from nostr_dvm_agent.core.event_handler import get_primary_input_text
from nostr_dvm_agent.services.base import BaseDVMService


class TranslationService(BaseDVMService):
    kind = 5000
    name = "Translation"
    description = "Text translation between languages powered by Gemini 3 Pro"
    default_cost_msats = 300

    def __init__(self, gemini: GeminiClient, cost_msats: int = 300) -> None:
        self._gemini = gemini
        self.default_cost_msats = cost_msats

    async def validate_input(self, job_data: dict[str, Any]) -> bool:
        text = get_primary_input_text(job_data)
        return len(text.strip()) > 0

    async def estimate_cost(self, job_data: dict[str, Any]) -> int:
        text = get_primary_input_text(job_data)
        tokens = self._gemini.estimate_tokens(text)
        if tokens > 1000:
            return self.default_cost_msats * 2
        return self.default_cost_msats

    async def execute(self, job_data: dict[str, Any]) -> str:
        text = get_primary_input_text(job_data)
        params = job_data.get("params", {})
        target_lang = params.get("language", params.get("target", "English"))
        source_lang = params.get("source", "auto")
        return await self._gemini.translate(text, target_language=target_lang, source_language=source_lang)
