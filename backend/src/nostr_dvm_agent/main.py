from __future__ import annotations

import asyncio
import signal
import sys

import structlog

from nostr_dvm_agent.advertising.nip89 import publish_handler_info
from nostr_dvm_agent.ai.gemini_client import GeminiClient
from nostr_dvm_agent.config import Settings
from nostr_dvm_agent.core.nostr_client import NostrClient
from nostr_dvm_agent.core.state_machine import StateMachine
from nostr_dvm_agent.db.store import Store
from nostr_dvm_agent.payment.lightning import LightningClient
from nostr_dvm_agent.payment.zap_verifier import verify_zap_receipt
from nostr_dvm_agent.services.base import BaseDVMService
from nostr_dvm_agent.services.discovery import DiscoveryService
from nostr_dvm_agent.services.image_generation import ImageGenerationService
from nostr_dvm_agent.services.text_extraction import TextExtractionService
from nostr_dvm_agent.services.text_generation import TextGenerationService
from nostr_dvm_agent.services.translation import TranslationService

logger = structlog.get_logger()


def configure_logging(level: str) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog, level.upper(), structlog.INFO)
        ),
    )


def build_services(settings: Settings, gemini: GeminiClient) -> dict[int, BaseDVMService]:
    return {
        5000: TranslationService(gemini, settings.cost_translation_msats),
        5001: TextGenerationService(gemini, settings.cost_text_generation_msats),
        5002: TextExtractionService(gemini, settings.cost_text_extraction_msats),
        5100: ImageGenerationService(gemini, settings.cost_image_generation_msats),
        5300: DiscoveryService(gemini, settings.default_cost_msats),
    }


async def run() -> None:
    settings = Settings()
    configure_logging(settings.log_level)

    logger.info("starting_sats_ai_agent", lightning=settings.lightning_address)

    store = Store(settings.db_path)
    await store.open()

    gemini = GeminiClient(settings)
    lightning = LightningClient(settings)
    nostr = NostrClient(settings)
    services = build_services(settings, gemini)

    state_machine = StateMachine(
        settings=settings,
        nostr=nostr,
        store=store,
        lightning=lightning,
        services=services,
    )

    async def on_job_request(event):
        await state_machine.handle_job_request(event)

    async def on_zap_receipt(event):
        zap_data = verify_zap_receipt(event)
        if zap_data and zap_data.get("event_id"):
            job = await store.get_job(zap_data["event_id"])
            if job and job.get("invoice_hash"):
                await state_machine.handle_payment_confirmed(job["invoice_hash"])

    nostr.on_job_request(on_job_request)
    nostr.on_zap_receipt(on_zap_receipt)

    await nostr.connect()
    await nostr.subscribe()
    await state_machine.start()

    await publish_handler_info(nostr, services, settings.lightning_address)

    logger.info(
        "agent_ready",
        pubkey=nostr.public_key.to_hex(),
        services=[s.name for s in services.values()],
        relays=settings.relay_urls,
    )

    shutdown_event = asyncio.Event()

    def _signal_handler():
        logger.info("shutdown_signal_received")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    event_loop_task = asyncio.create_task(nostr.run_event_loop())
    shutdown_task = asyncio.create_task(shutdown_event.wait())

    done, pending = await asyncio.wait(
        [event_loop_task, shutdown_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    logger.info("shutting_down")
    for task in pending:
        task.cancel()

    await state_machine.stop()
    await nostr.disconnect()
    await lightning.close()
    await store.close()

    logger.info("agent_stopped")


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
