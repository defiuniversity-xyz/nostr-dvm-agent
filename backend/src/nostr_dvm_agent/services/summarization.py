from __future__ import annotations

from typing import Any

from nostr_dvm_agent.ai.gemini_client import GeminiClient
from nostr_dvm_agent.core.event_handler import get_primary_input_text
from nostr_dvm_agent.services.base import BaseDVMService


class SummarizationService(BaseDVMService):
    """Summarization uses Kind 5001 but is distinguished by a 't' tag of 'summarize'."""

    kind = 5001
    name = "Summarization"
    description = "Text summarization powered by Gemini 3 Pro"
    default_cost_msats = 400

    def __init__(self, gemini: GeminiClient, cost_msats: int = 400) -> None:
        self._gemini = gemini
        self.default_cost_msats = cost_msats

    async def validate_input(self, job_data: dict[str, Any]) -> bool:
        text = get_primary_input_text(job_data)
        return len(text.strip()) > 0

    async def estimate_cost(self, job_data: dict[str, Any]) -> int:
        text = get_primary_input_text(job_data)
        tokens = self._gemini.estimate_tokens(text)
        if tokens > 5000:
            return self.default_cost_msats * 3
        if tokens > 1000:
            return self.default_cost_msats * 2
        return self.default_cost_msats

    async def execute(self, job_data: dict[str, Any]) -> str:
        text = get_primary_input_text(job_data)
        params = job_data.get("params", {})
        return await self._gemini.summarize(text, **params)
