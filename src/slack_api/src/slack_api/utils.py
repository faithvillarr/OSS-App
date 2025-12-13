from __future__ import annotations

from datetime import UTC, datetime


def sanitize_text(text: str, *, max_len: int = 4000) -> str:
    """Trim whitespace, collapse internal whitespace, and truncate to max_len."""
    t = " ".join(text.strip().split())
    if len(t) > max_len:
        t = t[:max_len]
    return t


def utc_ts() -> str:
    """Return a compact UTC timestamp like 'YYYYMMDDTHHMMSSZ'.

    This is stable, sortable, and test-friendly (string compare works).
    """
    now = datetime.now(UTC)
    return now.strftime("%Y%m%dT%H%M%SZ")
