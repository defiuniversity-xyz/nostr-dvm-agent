from __future__ import annotations

from typing import Any

from nostr_dvm_agent.ai.gemini_client import GeminiClient
from nostr_dvm_agent.services.base import BaseDVMService


class TextExtractionService(BaseDVMService):
    kind = 5002
    name = "Text Extraction"
    description = "Extract and analyze content from URLs"
    default_cost_msats = 200

    def __init__(self, gemini: GeminiClient, cost_msats: int = 200) -> None:
        self._gemini = gemini
        self.default_cost_msats = cost_msats

    async def validate_input(self, job_data: dict[str, Any]) -> bool:
        for inp in job_data.get("inputs", []):
            if inp.get("type") == "url" and inp.get("value", "").startswith("http"):
                return True
        return False

    async def estimate_cost(self, job_data: dict[str, Any]) -> int:
        return self.default_cost_msats

    async def execute(self, job_data: dict[str, Any]) -> str:
        url = ""
        for inp in job_data.get("inputs", []):
            if inp.get("type") == "url":
                url = inp["value"]
                break

        if not url:
            raise ValueError("No URL provided in job inputs")

        params = job_data.get("params", {})
        return await self._gemini.extract_text(url, **params)
