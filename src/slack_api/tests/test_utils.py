from __future__ import annotations

from slack_api import sanitize_text, utc_ts


def test_sanitize_text_trim_collapse_truncate() -> None:
    out = sanitize_text("  hi   team  ", max_len=5)
    # collapse -> "hi team", then truncate to 5 -> "hi te"
    assert out == "hi te"


def test_utc_ts_shape_and_order() -> None:
    t1 = utc_ts()
    t2 = utc_ts()
    assert isinstance(t1, str) and t1.endswith("Z") and len(t1) == 16
    assert isinstance(t2, str) and t2.endswith("Z") and len(t2) == 16
    # Lexicographically non-decreasing (may be equal within the same second)
    assert t1 <= t2
