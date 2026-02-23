"""Unit tests for the DVM job state store."""

import asyncio
import os
import tempfile

import pytest

from nostr_dvm_agent.db.store import JobState, Store


@pytest.fixture
async def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = Store(path)
    await s.open()
    yield s
    await s.close()
    os.unlink(path)


async def test_create_and_get_job(store: Store):
    await store.create_job("evt1", "pubkey1", 5001, {"inputs": []})
    job = await store.get_job("evt1")
    assert job is not None
    assert job["event_id"] == "evt1"
    assert job["customer_pubkey"] == "pubkey1"
    assert job["kind"] == 5001
    assert job["state"] == JobState.RECEIVED.value


async def test_state_transitions(store: Store):
    await store.create_job("evt2", "pubkey2", 5001)

    await store.update_state("evt2", JobState.WAITING_PAYMENT, bolt11="lnbc1...", amount_msats=500)
    job = await store.get_job("evt2")
    assert job["state"] == JobState.WAITING_PAYMENT.value
    assert job["bolt11"] == "lnbc1..."

    await store.update_state("evt2", JobState.PROCESSING)
    job = await store.get_job("evt2")
    assert job["state"] == JobState.PROCESSING.value

    await store.update_state("evt2", JobState.COMPLETED, result="Hello world")
    job = await store.get_job("evt2")
    assert job["state"] == JobState.COMPLETED.value
    assert job["result"] == "Hello world"


async def test_expire_stale_jobs(store: Store):
    await store.create_job("evt3", "pubkey3", 5001)
    await store.update_state("evt3", JobState.WAITING_PAYMENT)

    expired = await store.expire_stale_jobs(0)
    assert expired == 1

    job = await store.get_job("evt3")
    assert job["state"] == JobState.EXPIRED.value


async def test_get_job_by_invoice(store: Store):
    await store.create_job("evt4", "pubkey4", 5001)
    await store.update_state("evt4", JobState.WAITING_PAYMENT, invoice_hash="hash123")

    job = await store.get_job_by_invoice("hash123")
    assert job is not None
    assert job["event_id"] == "evt4"

    missing = await store.get_job_by_invoice("nonexistent")
    assert missing is None
