from __future__ import annotations

import json

import structlog
from nostr_sdk import EventBuilder, Kind, Tag

from nostr_dvm_agent.core.nostr_client import NostrClient
from nostr_dvm_agent.services.base import BaseDVMService

logger = structlog.get_logger()

HANDLER_INFO_KIND = 31990


async def publish_handler_info(
    nostr: NostrClient,
    services: dict[int, BaseDVMService],
    lightning_address: str,
) -> None:
    """Publish a NIP-89 Handler Information event (Kind 31990) to advertise DVM capabilities."""

    metadata = json.dumps({
        "name": "sats.ai",
        "display_name": "sats.ai DVM Agent",
        "about": "AI services powered by Gemini 3 Pro. Pay with Lightning sats. Text generation, translation, summarization, image generation, and more.",
        "picture": "",
        "lud16": lightning_address,
    })

    tags: list[Tag] = [
        Tag.parse(["d", "sats-ai-dvm"]),
    ]

    for kind, service in services.items():
        tags.append(Tag.parse(["k", str(kind)]))

    for kind, service in services.items():
        tags.append(Tag.parse([
            "nip90",
            str(kind),
            service.name,
            str(service.default_cost_msats),
        ]))

    builder = EventBuilder(Kind(HANDLER_INFO_KIND), metadata).tags(tags)
    await nostr.publish_event(builder)

    logger.info(
        "handler_info_published",
        kinds=list(services.keys()),
        services=[s.name for s in services.values()],
    )
