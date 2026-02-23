"""Unit tests for Zap Receipt verification logic."""

import hashlib
import json
from unittest.mock import MagicMock

from nostr_dvm_agent.payment.zap_verifier import verify_zap_receipt


def _make_mock_zap_receipt(
    *,
    kind: int = 9735,
    bolt11: str = "lnbc10u1p...",
    description_json: str | None = None,
    event_id: str = "abc123",
    amount_msats: int = 1000,
    valid_signature: bool = True,
):
    """Build a mock nostr_sdk Event for testing."""
    if description_json is None:
        zap_request = {
            "kind": 9734,
            "pubkey": "sender_pubkey_hex",
            "tags": [["amount", str(amount_msats)], ["e", event_id]],
            "content": "",
        }
        description_json = json.dumps(zap_request)

    tag_data = [
        ["bolt11", bolt11],
        ["description", description_json],
        ["e", event_id],
        ["p", "recipient_pubkey_hex"],
    ]

    mock_tags = []
    for td in tag_data:
        tag = MagicMock()
        tag.as_vec.return_value = td
        mock_tags.append(tag)

    tags_container = MagicMock()
    tags_container.to_vec.return_value = mock_tags

    event = MagicMock()
    event.kind.return_value.as_u16.return_value = kind
    event.tags.return_value = tags_container
    event.id.return_value.to_hex.return_value = "receipt_event_id_hex"
    event.author.return_value.to_hex.return_value = "receipt_author_hex"

    if valid_signature:
        event.verify.return_value = None
    else:
        event.verify.side_effect = Exception("Invalid signature")

    return event


def test_valid_zap_receipt():
    event = _make_mock_zap_receipt()
    result = verify_zap_receipt(event)

    assert result is not None
    assert result["event_id"] == "abc123"
    assert result["amount_msats"] == 1000
    assert result["bolt11"] == "lnbc10u1p..."
    assert result["payer_pubkey"] == "sender_pubkey_hex"
    assert result["receipt_author"] == "receipt_author_hex"
    assert len(result["description_hash"]) == 64


def test_wrong_kind_rejected():
    event = _make_mock_zap_receipt(kind=9734)
    result = verify_zap_receipt(event)
    assert result is None


def test_invalid_signature_rejected():
    event = _make_mock_zap_receipt(valid_signature=False)
    result = verify_zap_receipt(event)
    assert result is None


def test_invalid_description_json_rejected():
    event = _make_mock_zap_receipt(description_json="not valid json {{{")
    result = verify_zap_receipt(event)
    assert result is None


def test_wrong_zap_request_kind_rejected():
    bad_zr = json.dumps({"kind": 1, "pubkey": "abc", "tags": [], "content": ""})
    event = _make_mock_zap_receipt(description_json=bad_zr)
    result = verify_zap_receipt(event)
    assert result is None


def test_description_hash_is_sha256():
    zr = {"kind": 9734, "pubkey": "abc", "tags": [["amount", "500"]], "content": ""}
    desc_json = json.dumps(zr)
    expected_hash = hashlib.sha256(desc_json.encode()).hexdigest()

    event = _make_mock_zap_receipt(description_json=desc_json)
    result = verify_zap_receipt(event)

    assert result is not None
    assert result["description_hash"] == expected_hash


def test_amount_verification():
    event = _make_mock_zap_receipt(amount_msats=500)
    result = verify_zap_receipt(event, expected_amount_msats=1000)
    assert result is None

    result = verify_zap_receipt(event, expected_amount_msats=500)
    assert result is not None

    result = verify_zap_receipt(event, expected_amount_msats=200)
    assert result is not None
