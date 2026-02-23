from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

from nostr_dvm_agent.config import Settings

logger = structlog.get_logger()


class LightningClient:
    """Generates BOLT-11 invoices via LNURL-pay and verifies payments via Strike API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http = httpx.AsyncClient(timeout=15)
        self._lnurlp_meta: dict[str, Any] | None = None

    async def close(self) -> None:
        await self._http.aclose()

    async def _fetch_lnurlp_metadata(self) -> dict[str, Any] | None:
        if self._lnurlp_meta:
            return self._lnurlp_meta

        url = self._settings.lnurlp_url
        logger.info("fetching_lnurlp", url=url)

        try:
            resp = await self._http.get(url)
            resp.raise_for_status()
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
            resp = await self._http.get(invoice_url)
            resp.raise_for_status()
            data = resp.json()

            bolt11 = data.get("pr")
            if not bolt11:
                logger.error("lnurlp_no_invoice", response=data)
                return None

            payment_hash = self._extract_payment_hash(bolt11)

            logger.info("invoice_created", amount_msats=amount_msats, hash=payment_hash[:16] if payment_hash else "?")
            return {
                "bolt11": bolt11,
                "payment_hash": payment_hash or "",
                "amount_msats": amount_msats,
            }

        except Exception:
            logger.exception("invoice_creation_failed")
            return None

    def _extract_payment_hash(self, bolt11: str) -> str | None:
        """Best-effort extraction of payment hash from BOLT-11 string."""
        try:
            # nostr-sdk or a dedicated bolt11 parser would be ideal here;
            # for now we store the bolt11 itself as the lookup key
            return bolt11[-64:] if len(bolt11) > 64 else bolt11
        except Exception:
            return None

    async def check_payment(self, payment_hash: str) -> bool:
        """Poll Strike API (or LNbits) to check if an invoice has been paid."""
        if not self._settings.strike_api_key:
            logger.debug("no_strike_api_key_skipping_poll")
            return False

        try:
            resp = await self._http.get(
                f"https://api.strike.me/v1/invoices/{payment_hash}",
                headers={"Authorization": f"Bearer {self._settings.strike_api_key}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                paid = data.get("state") == "PAID"
                if paid:
                    logger.info("strike_payment_confirmed", hash=payment_hash[:16])
                return paid
        except Exception:
            logger.exception("strike_payment_check_failed")

        return False

    async def poll_payment(self, payment_hash: str, timeout_secs: int = 300) -> bool:
        """Poll for payment confirmation with exponential backoff."""
        elapsed = 0
        interval = 2

        while elapsed < timeout_secs:
            if await self.check_payment(payment_hash):
                return True
            await asyncio.sleep(interval)
            elapsed += interval
            interval = min(interval * 1.5, 15)

        logger.warning("payment_poll_timeout", hash=payment_hash[:16])
        return False
