from __future__ import annotations

import re
from typing import Any

import httpx
import structlog

from nostr_dvm_agent.ai.gemini_client import GeminiClient
from nostr_dvm_agent.services.base import BaseDVMService

logger = structlog.get_logger()

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s{3,}")


def strip_html(html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = HTML_TAG_RE.sub(" ", text)
    text = WHITESPACE_RE.sub("\n\n", text)
    return text.strip()


class TextExtractionService(BaseDVMService):
    kind = 5002
    name = "Text Extraction"
    description = "Extract and analyze content from URLs"
    default_cost_msats = 200

    def __init__(self, gemini: GeminiClient, cost_msats: int = 200) -> None:
        self._gemini = gemini
        self.default_cost_msats = cost_msats
        self._http = httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "sats.ai DVM Agent/0.1"},
        )

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

        logger.info("fetching_url", url=url)
        try:
            resp = await self._http.get(url)
            resp.raise_for_status()
            raw_content = resp.text
        except httpx.TimeoutException:
            raise ValueError(f"Timeout fetching URL: {url}")
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"HTTP {exc.response.status_code} fetching URL: {url}")
        except Exception as exc:
            raise ValueError(f"Failed to fetch URL: {url} -- {exc}")

        content_type = resp.headers.get("content-type", "")
        if "html" in content_type:
            text_content = strip_html(raw_content)
        else:
            text_content = raw_content

        if len(text_content) < 10:
            raise ValueError(f"No meaningful content extracted from {url}")

        logger.info("url_fetched", url=url, content_len=len(text_content))

        params = job_data.get("params", {})
        return await self._gemini.extract_text(url, content=text_content, **params)
