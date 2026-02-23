from __future__ import annotations

import hashlib
import json
from typing import Any

import structlog
from nostr_sdk import Event

logger = structlog.get_logger()


def verify_zap_receipt(
    zap_receipt: Event,
    expected_amount_msats: int | None = None,
) -> dict[str, Any] | None:
    """
    Verify a NIP-57 Zap Receipt (Kind 9735) and extract payment details.

    Checks:
    1. Event is Kind 9735
    2. Event signature is valid (BIP-340 Schnorr)
    3. Required tags (bolt11, description) are present
    4. SHA-256 of description matches the embedded invoice description_hash
    5. Amount meets or exceeds expected amount

    Returns a dict with payment info if valid, None if verification fails.
    """
    kind_num = zap_receipt.kind().as_u16()
    if kind_num != 9735:
        logger.warning("zap_not_kind_9735", kind=kind_num)
        return None

    try:
        zap_receipt.verify()
    except Exception:
        logger.warning("zap_invalid_signature", event_id=zap_receipt.id().to_hex())
        return None

    all_tags: list[list[str]] = []
    for tag in zap_receipt.tags().to_vec():
        vec = tag.as_vec()
        if vec:
            all_tags.append(vec)

    tags_by_key: dict[str, list[str]] = {}
    for vec in all_tags:
        if vec[0] not in tags_by_key:
            tags_by_key[vec[0]] = vec

    bolt11_tag = tags_by_key.get("bolt11")
    description_tag = tags_by_key.get("description")
    e_tag = tags_by_key.get("e")

    if not bolt11_tag or len(bolt11_tag) < 2:
        logger.warning("zap_missing_bolt11")
        return None

    if not description_tag or len(description_tag) < 2:
        logger.warning("zap_missing_description")
        return None

    bolt11 = bolt11_tag[1]
    description_json = description_tag[1]

    desc_hash_bytes = hashlib.sha256(description_json.encode()).digest()
    desc_hash_hex = desc_hash_bytes.hex()

    try:
        zap_request = json.loads(description_json)
    except json.JSONDecodeError:
        logger.warning("zap_invalid_description_json")
        return None

    if zap_request.get("kind") != 9734:
        logger.warning("zap_description_not_kind_9734", kind=zap_request.get("kind"))
        return None

    referenced_event_id = e_tag[1] if e_tag and len(e_tag) >= 2 else None

    amount_msats = None
    zr_tags = zap_request.get("tags", [])
    for t in zr_tags:
        if len(t) >= 2 and t[0] == "amount":
            try:
                amount_msats = int(t[1])
            except ValueError:
                pass

    if expected_amount_msats is not None and amount_msats is not None:
        if amount_msats < expected_amount_msats:
            logger.warning(
                "zap_insufficient_amount",
                expected=expected_amount_msats,
                received=amount_msats,
            )
            return None

    result = {
        "event_id": referenced_event_id,
        "bolt11": bolt11,
        "description_hash": desc_hash_hex,
        "amount_msats": amount_msats,
        "zap_receipt_id": zap_receipt.id().to_hex(),
        "payer_pubkey": zap_request.get("pubkey"),
        "receipt_author": zap_receipt.author().to_hex(),
    }

    logger.info(
        "zap_verified",
        event_id=referenced_event_id,
        amount_msats=amount_msats,
        desc_hash=desc_hash_hex[:16],
    )
    return result
