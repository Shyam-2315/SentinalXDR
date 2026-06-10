from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


Event = dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def make_event(
    *,
    event_type: str,
    severity: str,
    title: str,
    description: str,
    raw_event: dict[str, Any],
    normalized_fields: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    timestamp: str | None = None,
) -> Event:
    return {
        "event_type": event_type,
        "severity": severity,
        "source": "linux",
        "title": title,
        "description": description,
        "raw_event": raw_event,
        "normalized_fields": normalized_fields or {},
        "tags": tags or [],
        "timestamp": timestamp or utc_now_iso(),
    }


def batch_events(events: list[Event], batch_size: int) -> list[list[Event]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    return [events[index : index + batch_size] for index in range(0, len(events), batch_size)]
