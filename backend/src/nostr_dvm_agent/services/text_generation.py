from __future__ import annotations

from typing import Any

from nostr_dvm_agent.ai.gemini_client import GeminiClient
from nostr_dvm_agent.core.event_handler import get_primary_input_text
from nostr_dvm_agent.services.base import BaseDVMService


class TextGenerationService(BaseDVMService):
    """Handles Kind 5001 for both text generation and summarization.

    If the job request includes a param tag with task=summarize (or a t tag
    containing "summarize"), the service delegates to Gemini's summarize method.
    Otherwise it uses standard text generation.
    """

    kind = 5001
    name = "Text Generation"
    description = "LLM text generation and summarization powered by Gemini"
    default_cost_msats = 500

    def __init__(self, gemini: GeminiClient, cost_msats: int = 500) -> None:
        self._gemini = gemini
        self.default_cost_msats = cost_msats

    def _is_summarize_task(self, job_data: dict[str, Any]) -> bool:
        params = job_data.get("params", {})
        if params.get("task") == "summarize":
            return True
        for topic in job_data.get("topics", []):
            if "summarize" in topic.lower():
                return True
        return False

    async def validate_input(self, job_data: dict[str, Any]) -> bool:
        text = get_primary_input_text(job_data)
        return len(text.strip()) > 0

    async def estimate_cost(self, job_data: dict[str, Any]) -> int:
        text = get_primary_input_text(job_data)
        tokens = self._gemini.estimate_tokens(text)
        base = self.default_cost_msats
        if self._is_summarize_task(job_data) and tokens > 5000:
            return base * 3
        if tokens > 2000:
            return base * 3
        if tokens > 500:
            return base * 2
        return base

    async def execute(self, job_data: dict[str, Any]) -> str:
        text = get_primary_input_text(job_data)
        params = job_data.get("params", {})

        if self._is_summarize_task(job_data):
            return await self._gemini.summarize(text, **params)

        return await self._gemini.generate_text(text, **params)
