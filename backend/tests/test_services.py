"""Unit tests for DVM service input validation."""

import pytest

from nostr_dvm_agent.core.event_handler import extract_job_input, get_primary_input_text


def _make_job_data(inputs=None, content="", params=None):
    return {
        "event_id": "abc123",
        "pubkey": "pubkey1",
        "kind": 5001,
        "content": content,
        "inputs": inputs or [],
        "params": params or {},
        "output_mime": None,
        "bid_msats": None,
        "encrypted": False,
    }


def test_get_primary_input_text_from_inputs():
    job = _make_job_data(inputs=[{"value": "Hello world", "type": "text"}])
    assert get_primary_input_text(job) == "Hello world"


def test_get_primary_input_text_from_content():
    job = _make_job_data(content="Fallback content")
    assert get_primary_input_text(job) == "Fallback content"


def test_get_primary_input_text_empty():
    job = _make_job_data()
    assert get_primary_input_text(job) == ""


def test_get_primary_input_prefers_inputs_over_content():
    job = _make_job_data(
        inputs=[{"value": "From input", "type": "text"}],
        content="From content",
    )
    assert get_primary_input_text(job) == "From input"
