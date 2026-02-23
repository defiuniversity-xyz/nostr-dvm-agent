from __future__ import annotations

import asyncio
from typing import Any

import structlog
from nostr_sdk import Event, Tag

from nostr_dvm_agent.config import Settings
from nostr_dvm_agent.core.event_handler import extract_job_input, get_primary_input_text
from nostr_dvm_agent.core.nostr_client import NostrClient
from nostr_dvm_agent.db.store import JobState, Store
from nostr_dvm_agent.payment.lightning import LightningClient
from nostr_dvm_agent.services.base import BaseDVMService

logger = structlog.get_logger()


class StateMachine:
    """Orchestrates the NIP-90 job lifecycle from request to result delivery."""

    def __init__(
        self,
        settings: Settings,
        nostr: NostrClient,
        store: Store,
        lightning: LightningClient,
        services: dict[int, BaseDVMService],
    ) -> None:
        self._settings = settings
        self._nostr = nostr
        self._store = store
        self._lightning = lightning
        self._services = services
        self._expiry_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._expiry_task = asyncio.create_task(self._expiry_loop())
        logger.info("state_machine_started", services=list(self._services.keys()))

    async def stop(self) -> None:
        if self._expiry_task:
            self._expiry_task.cancel()

    async def handle_job_request(self, event: Event) -> None:
        job_data = extract_job_input(event)
        event_id = job_data["event_id"]
        kind = job_data["kind"]
        customer = job_data["pubkey"]

        service = self._services.get(kind)
        if not service:
            logger.warning("unsupported_kind", kind=kind, event_id=event_id)
            return

        if not await service.validate_input(job_data):
            logger.warning("invalid_input", event_id=event_id)
            await self._nostr.publish_feedback(
                event_id, customer, "error", content="Invalid or missing input data."
            )
            return

        await self._store.create_job(event_id, customer, kind, input_data=job_data)

        cost = await service.estimate_cost(job_data)
        invoice_data = await self._lightning.create_invoice(cost, f"sats.ai DVM job {event_id[:8]}")

        if not invoice_data:
            logger.error("invoice_creation_failed", event_id=event_id)
            await self._transition(event_id, customer, JobState.FAILED, error="Invoice creation failed")
            return

        await self._store.update_state(
            event_id,
            JobState.WAITING_PAYMENT,
            bolt11=invoice_data["bolt11"],
            invoice_hash=invoice_data.get("payment_hash", ""),
            amount_msats=cost,
        )

        await self._nostr.publish_feedback(
            event_id,
            customer,
            "payment-required",
            extra_tags=[
                Tag.parse(["amount", str(cost), invoice_data["bolt11"]]),
            ],
        )
        logger.info("payment_required", event_id=event_id, amount_msats=cost)

    async def handle_payment_confirmed(self, invoice_hash: str) -> None:
        job = await self._store.get_job_by_invoice(invoice_hash)
        if not job:
            logger.warning("payment_no_matching_job", invoice_hash=invoice_hash)
            return

        event_id = job["event_id"]
        customer = job["customer_pubkey"]
        kind = job["kind"]

        if job["state"] != JobState.WAITING_PAYMENT.value:
            logger.info("payment_already_processed", event_id=event_id)
            return

        await self._transition(event_id, customer, JobState.PROCESSING)
        await self._nostr.publish_feedback(event_id, customer, "processing")

        asyncio.create_task(self._execute_job(event_id, customer, kind))

    async def _execute_job(self, event_id: str, customer: str, kind: int) -> None:
        service = self._services.get(kind)
        if not service:
            await self._transition(event_id, customer, JobState.FAILED, error="Service not found")
            return

        job = await self._store.get_job(event_id)
        if not job:
            return

        import json
        job_data = json.loads(job["input_data"]) if job["input_data"] else {}

        try:
            result = await service.execute(job_data)
            await self._store.update_state(event_id, JobState.COMPLETED, result=result)
            await self._nostr.publish_result(event_id, customer, kind, result)
            logger.info("job_completed", event_id=event_id)

        except Exception as exc:
            error_msg = str(exc)
            await self._transition(event_id, customer, JobState.FAILED, error=error_msg)
            await self._nostr.publish_feedback(
                event_id, customer, "error", content=error_msg
            )
            logger.exception("job_execution_failed", event_id=event_id)

    async def _transition(
        self,
        event_id: str,
        customer: str,
        state: JobState,
        **extra: Any,
    ) -> None:
        await self._store.update_state(event_id, state, **extra)
        logger.info("state_transition", event_id=event_id, state=state.value)

    async def _expiry_loop(self) -> None:
        while True:
            try:
                expired = await self._store.expire_stale_jobs(self._settings.payment_timeout_secs)
                if expired:
                    logger.info("expired_jobs", count=expired)
            except Exception:
                logger.exception("expiry_loop_error")
            await asyncio.sleep(30)
