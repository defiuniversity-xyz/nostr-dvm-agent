from __future__ import annotations

import json
import time
from enum import Enum
from typing import Any

import aiosqlite


class JobState(str, Enum):
    RECEIVED = "received"
    PAYMENT_REQUIRED = "payment_required"
    WAITING_PAYMENT = "waiting_payment"
    PROCESSING = "processing"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class Store:
    """SQLite-backed persistence for DVM job state."""

    def __init__(self, db_path: str = "dvm_agent.db") -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def open(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._migrate()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def _migrate(self) -> None:
        assert self._db
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                event_id       TEXT PRIMARY KEY,
                customer_pubkey TEXT NOT NULL,
                kind           INTEGER NOT NULL,
                state          TEXT NOT NULL DEFAULT 'received',
                input_data     TEXT,
                bolt11         TEXT,
                invoice_hash   TEXT,
                amount_msats   INTEGER,
                result         TEXT,
                error          TEXT,
                created_at     REAL NOT NULL,
                updated_at     REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state);
            CREATE INDEX IF NOT EXISTS idx_jobs_invoice ON jobs(invoice_hash);
        """)
        await self._db.commit()

    async def create_job(
        self,
        event_id: str,
        customer_pubkey: str,
        kind: int,
        input_data: dict[str, Any] | None = None,
    ) -> None:
        assert self._db
        now = time.time()
        await self._db.execute(
            """INSERT OR IGNORE INTO jobs
               (event_id, customer_pubkey, kind, state, input_data, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event_id, customer_pubkey, kind, JobState.RECEIVED.value,
             json.dumps(input_data) if input_data else None, now, now),
        )
        await self._db.commit()

    _ALLOWED_COLUMNS = frozenset({
        "bolt11", "invoice_hash", "amount_msats", "result", "error", "input_data",
    })

    async def update_state(
        self,
        event_id: str,
        state: JobState,
        **extra: Any,
    ) -> None:
        assert self._db
        sets = ["state = ?", "updated_at = ?"]
        params: list[Any] = [state.value, time.time()]
        for key, val in extra.items():
            if key not in self._ALLOWED_COLUMNS:
                raise ValueError(f"Disallowed column name: {key}")
            sets.append(f"{key} = ?")
            params.append(val)
        params.append(event_id)
        await self._db.execute(
            f"UPDATE jobs SET {', '.join(sets)} WHERE event_id = ?",
            params,
        )
        await self._db.commit()

    async def get_job(self, event_id: str) -> dict[str, Any] | None:
        assert self._db
        cursor = await self._db.execute("SELECT * FROM jobs WHERE event_id = ?", (event_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_job_by_invoice(self, invoice_hash: str) -> dict[str, Any] | None:
        assert self._db
        cursor = await self._db.execute(
            "SELECT * FROM jobs WHERE invoice_hash = ?", (invoice_hash,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_jobs_in_state(self, state: JobState) -> list[dict[str, Any]]:
        assert self._db
        cursor = await self._db.execute("SELECT * FROM jobs WHERE state = ?", (state.value,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def expire_stale_jobs(self, timeout_secs: float) -> int:
        assert self._db
        cutoff = time.time() - timeout_secs
        cursor = await self._db.execute(
            """UPDATE jobs SET state = ?, updated_at = ?
               WHERE state = ? AND updated_at < ?""",
            (JobState.EXPIRED.value, time.time(), JobState.WAITING_PAYMENT.value, cutoff),
        )
        await self._db.commit()
        return cursor.rowcount
