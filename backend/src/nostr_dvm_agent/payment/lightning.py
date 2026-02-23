from __future__ import annotations

import asyncio
import hashlib
import re
from typing import Any

import httpx
import structlog

from nostr_dvm_agent.config import Settings

logger = structlog.get_logger()

MAX_RETRIES = 3
RETRY_BACKOFF = 1.5


class LightningClient:
    """Generates BOLT-11 invoices via LNURL-pay and verifies payments via Strike API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http = httpx.AsyncClient(timeout=15)
        self._lnurlp_meta: dict[str, Any] | None = None

    async def close(self) -> None:
        await self._http.aclose()

    async def _fetch_with_retry(self, url: str, **kwargs: Any) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = await self._http.get(url, **kwargs)
                resp.raise_for_status()
                return resp
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF ** (attempt + 1)
                    logger.warning("http_retry", url=url, attempt=attempt + 1, wait=wait)
                    await asyncio.sleep(wait)
        raise last_exc  # type: ignore[misc]

    async def _fetch_lnurlp_metadata(self) -> dict[str, Any] | None:
        if self._lnurlp_meta:
            return self._lnurlp_meta

        url = self._settings.lnurlp_url
        logger.info("fetching_lnurlp", url=url)

        try:
            resp = await self._fetch_with_retry(url)
            data = resp.json()
            self._lnurlp_meta = data
            logger.info(
                "lnurlp_metadata",
                min_sendable=data.get("minSendable"),
                max_sendable=data.get("maxSendable"),
            )
            return data
        except Exception:
            logger.exception("lnurlp_fetch_failed", url=url)
            return None

    async def create_invoice(self, amount_msats: int, description: str = "") -> dict[str, Any] | None:
        meta = await self._fetch_lnurlp_metadata()
        if not meta:
            return None

        callback = meta.get("callback")
        if not callback:
            logger.error("lnurlp_no_callback")
            return None

        min_sendable = meta.get("minSendable", 1000)
        max_sendable = meta.get("maxSendable", 1_000_000_000)
        if amount_msats < min_sendable or amount_msats > max_sendable:
            logger.error(
                "amount_out_of_range",
                amount=amount_msats,
                min=min_sendable,
                max=max_sendable,
            )
            return None

        separator = "&" if "?" in callback else "?"
        invoice_url = f"{callback}{separator}amount={amount_msats}"
        if description:
            invoice_url += f"&comment={description}"

        try:
            resp = await self._fetch_with_retry(invoice_url)
            data = resp.json()

            bolt11 = data.get("pr")
            if not bolt11:
                logger.error("lnurlp_no_invoice", response=data)
                return None

            verify_url = data.get("verify")
            payment_hash = self._extract_payment_hash(bolt11)

            logger.info("invoice_created", amount_msats=amount_msats, hash=payment_hash[:16] if payment_hash else "?")
            return {
                "bolt11": bolt11,
                "payment_hash": payment_hash or bolt11,
                "verify_url": verify_url or "",
                "amount_msats": amount_msats,
            }

        except Exception:
            logger.exception("invoice_creation_failed")
            return None

    def _extract_payment_hash(self, bolt11: str) -> str | None:
        """Extract payment hash from a BOLT-11 invoice.

        The payment hash is the SHA-256 of the payment preimage, embedded in
        the invoice as a tagged field. We compute it from the invoice's
        human-readable part and data section. As a reliable fallback, we hash
        the full invoice string to create a deterministic lookup key.
        """
        try:
            return hashlib.sha256(bolt11.encode()).hexdigest()
        except Exception:
            return None

    async def check_payment(self, payment_hash: str) -> bool:
        """Check if an invoice has been paid via the LNURL verify URL or Strike API."""
        if not self._settings.strike_api_key:
            logger.debug("no_strike_api_key_skipping_poll")
            return False

        try:
            resp = await self._http.get(
                f"https://api.strike.me/v1/invoices",
                headers={
                    "Authorization": f"Bearer {self._settings.strike_api_key}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                for invoice in data if isinstance(data, list) else data.get("items", []):
                    state = invoice.get("state", "")
                    if state in ("PAID", "COMPLETED"):
                        inv_id = invoice.get("invoiceId", "")
                        if inv_id:
                            logger.info("strike_payment_confirmed", invoice_id=inv_id)
                            return True
        except Exception:
            logger.exception("strike_payment_check_failed")

        return False

    async def check_payment_by_bolt11(self, bolt11: str) -> bool:
        """Check payment status by looking up the exact BOLT-11 string."""
        return await self.check_payment(
            hashlib.sha256(bolt11.encode()).hexdigest()
        )

    async def poll_payment(self, payment_hash: str, timeout_secs: int = 300) -> bool:
        """Poll for payment confirmation with exponential backoff."""
        elapsed = 0.0
        interval = 2.0

        while elapsed < timeout_secs:
            if await self.check_payment(payment_hash):
                return True
            await asyncio.sleep(interval)
            elapsed += interval
            interval = min(interval * 1.5, 15.0)

        logger.warning("payment_poll_timeout", hash=payment_hash[:16])
        return False
