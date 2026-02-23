from __future__ import annotations

from typing import Any

import structlog
from nostr_sdk import Event

logger = structlog.get_logger()


def extract_job_input(event: Event) -> dict[str, Any]:
    """Parse NIP-90 job request tags into a structured dict."""
    result: dict[str, Any] = {
        "event_id": event.id().to_hex(),
        "pubkey": event.author().to_hex(),
        "kind": event.kind().as_u16(),
        "content": event.content(),
        "inputs": [],
        "params": {},
        "output_mime": None,
        "bid_msats": None,
        "encrypted": False,
    }

    for tag in event.tags().to_vec():
        tag_vec = tag.as_vec()
        if len(tag_vec) < 2:
            continue

        key = tag_vec[0]

        if key == "i":
            input_entry: dict[str, str] = {"value": tag_vec[1]}
            if len(tag_vec) > 2:
                input_entry["type"] = tag_vec[2]
            if len(tag_vec) > 3:
                input_entry["relay"] = tag_vec[3]
            result["inputs"].append(input_entry)

        elif key == "param":
            if len(tag_vec) >= 3:
                result["params"][tag_vec[1]] = tag_vec[2]

        elif key == "output":
            result["output_mime"] = tag_vec[1]

        elif key == "bid":
            try:
                result["bid_msats"] = int(tag_vec[1])
            except ValueError:
                pass

        elif key == "encrypted":
            result["encrypted"] = True

        elif key == "t":
            result.setdefault("topics", []).append(tag_vec[1])

    return result


def get_primary_input_text(job_data: dict[str, Any]) -> str:
    """Return the first text input, falling back to event content."""
    for inp in job_data.get("inputs", []):
        input_type = inp.get("type", "text")
        if input_type == "text":
            return inp["value"]

    if job_data.get("content"):
        return job_data["content"]

    return ""
