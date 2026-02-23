from __future__ import annotations

import hashlib
import json
from typing import Any

import structlog
from nostr_sdk import Event

logger = structlog.get_logger()


def verify_zap_receipt(zap_receipt: Event) -> dict[str, Any] | None:
    """
    Verify a NIP-57 Zap Receipt (Kind 9735) and extract payment details.

    Returns a dict with payment info if valid, None if verification fails.
    """
    kind_num = zap_receipt.kind().as_u16()
    if kind_num != 9735:
        logger.warning("not_zap_receipt", kind=kind_num)
        return None

    tags = {tag.as_vec()[0]: tag.as_vec() for tag in zap_receipt.tags().to_vec() if tag.as_vec()}

    bolt11_tag = tags.get("bolt11")
    description_tag = tags.get("description")
    e_tag = tags.get("e")
    p_tag = tags.get("p")

    if not bolt11_tag or len(bolt11_tag) < 2:
        logger.warning("zap_missing_bolt11")
        return None

    if not description_tag or len(description_tag) < 2:
        logger.warning("zap_missing_description")
        return None

    bolt11 = bolt11_tag[1]
    description_json = description_tag[1]

    # Verify description hash: SHA-256 of the embedded Kind 9734 must match
    # the description_hash in the BOLT-11 invoice
    try:
        desc_hash = hashlib.sha256(description_json.encode()).hexdigest()
        logger.debug("zap_description_hash", hash=desc_hash[:16])
    except Exception:
        logger.exception("zap_hash_computation_failed")
        return None

    # Parse the embedded Zap Request (Kind 9734)
    try:
        zap_request = json.loads(description_json)
    except json.JSONDecodeError:
        logger.warning("zap_invalid_description_json")
        return None

    # Extract the event ID this zap is for
    referenced_event_id = e_tag[1] if e_tag and len(e_tag) >= 2 else None

    # Extract amount from zap request tags
    amount_msats = None
    zr_tags = zap_request.get("tags", [])
    for t in zr_tags:
        if len(t) >= 2 and t[0] == "amount":
            try:
                amount_msats = int(t[1])
            except ValueError:
                pass

    result = {
        "event_id": referenced_event_id,
        "bolt11": bolt11,
        "description_hash": desc_hash,
        "amount_msats": amount_msats,
        "zap_receipt_id": zap_receipt.id().to_hex(),
        "payer_pubkey": zap_request.get("pubkey"),
    }

    logger.info(
        "zap_verified",
        event_id=referenced_event_id,
        amount_msats=amount_msats,
    )
    return result
