from __future__ import annotations

import asyncio
from typing import Callable, Awaitable

import structlog
from nostr_sdk import (
    Client,
    Event,
    EventBuilder,
    Filter,
    Keys,
    Kind,
    NostrSigner,
    PublicKey,
    Tag,
    Timestamp,
)

from nostr_dvm_agent.config import Settings

logger = structlog.get_logger()

DVM_REQUEST_KINDS = [5000, 5001, 5002, 5100, 5300]
ZAP_RECEIPT_KIND = 9735

EventCallback = Callable[[Event], Awaitable[None]]


class NostrClient:
    """Manages relay connections, subscriptions, and event publishing."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._keys = Keys.parse(settings.nostr_private_key)
        signer = NostrSigner.keys(self._keys)
        self._client = Client(signer)
        self._on_job_request: EventCallback | None = None
        self._on_zap_receipt: EventCallback | None = None
        self._running = False

    @property
    def public_key(self) -> PublicKey:
        return self._keys.public_key()

    @property
    def keys(self) -> Keys:
        return self._keys

    def on_job_request(self, callback: EventCallback) -> None:
        self._on_job_request = callback

    def on_zap_receipt(self, callback: EventCallback) -> None:
        self._on_zap_receipt = callback

    async def connect(self) -> None:
        for url in self._settings.relay_urls:
            await self._client.add_relay(url)
            logger.info("relay_added", url=url)
        await self._client.connect()
        logger.info("connected_to_relays", count=len(self._settings.relay_urls))

    async def subscribe(self) -> None:
        now = Timestamp.now()

        job_filter = Filter().kinds(
            [Kind(k) for k in DVM_REQUEST_KINDS]
        ).since(now)

        zap_filter = (
            Filter()
            .kind(Kind(ZAP_RECEIPT_KIND))
            .pubkeys([self.public_key])
            .since(now)
        )

        await self._client.subscribe(
            [job_filter, zap_filter],
            None,
        )
        logger.info(
            "subscribed",
            job_kinds=DVM_REQUEST_KINDS,
            zap_kind=ZAP_RECEIPT_KIND,
        )

    async def run_event_loop(self) -> None:
        self._running = True
        logger.info("event_loop_started")

        while self._running:
            try:
                await self._client.handle_notifications(self._handle_notification)
            except Exception:
                logger.exception("notification_handler_error")
                await asyncio.sleep(2)

    async def _handle_notification(self, relay_url, subscription_id, event: Event) -> bool:
        kind_num = event.kind().as_u16()

        if kind_num in DVM_REQUEST_KINDS and self._on_job_request:
            logger.info("job_request_received", event_id=event.id().to_hex(), kind=kind_num)
            try:
                await self._on_job_request(event)
            except Exception:
                logger.exception("job_request_handler_error", event_id=event.id().to_hex())

        elif kind_num == ZAP_RECEIPT_KIND and self._on_zap_receipt:
            logger.info("zap_receipt_received", event_id=event.id().to_hex())
            try:
                await self._on_zap_receipt(event)
            except Exception:
                logger.exception("zap_receipt_handler_error", event_id=event.id().to_hex())

        return False

    async def publish_event(self, event_builder: EventBuilder) -> Event:
        output = await self._client.send_event_builder(event_builder)
        event_id = output.id().to_hex()
        logger.info("event_published", event_id=event_id)
        return output

    async def publish_feedback(
        self,
        job_event_id: str,
        customer_pubkey: str,
        status: str,
        *,
        extra_tags: list[Tag] | None = None,
        content: str = "",
    ) -> None:
        tags = [
            Tag.parse(["e", job_event_id]),
            Tag.parse(["p", customer_pubkey]),
            Tag.parse(["status", status]),
        ]
        if extra_tags:
            tags.extend(extra_tags)

        builder = EventBuilder(Kind(7000), content).tags(tags)
        await self.publish_event(builder)
        logger.info("feedback_published", job=job_event_id, status=status)

    async def publish_result(
        self,
        job_event_id: str,
        customer_pubkey: str,
        request_kind: int,
        content: str,
        *,
        extra_tags: list[Tag] | None = None,
    ) -> None:
        result_kind = request_kind + 1000
        tags = [
            Tag.parse(["e", job_event_id]),
            Tag.parse(["p", customer_pubkey]),
            Tag.parse(["status", "success"]),
        ]
        if extra_tags:
            tags.extend(extra_tags)

        builder = EventBuilder(Kind(result_kind), content).tags(tags)
        await self.publish_event(builder)
        logger.info("result_published", job=job_event_id, result_kind=result_kind)

    async def disconnect(self) -> None:
        self._running = False
        await self._client.disconnect()
        logger.info("disconnected")
