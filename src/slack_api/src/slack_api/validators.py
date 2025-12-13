from __future__ import annotations

import re

from .errors import InvalidIdError, ValidationError
from .utils import sanitize_text

# Slack-like id shapes:
# Channels: "C" followed by 2+ uppercase letters or digits.
# Users:    "U" followed by 2+ uppercase letters or digits.
_CHANNEL_ID_RE = re.compile(r"^C[0-9A-Z]{2,}$")
_USER_ID_RE = re.compile(r"^U[0-9A-Z]{2,}$")


def is_valid_channel_id(value: str) -> bool:
    return bool(_CHANNEL_ID_RE.fullmatch(value))


def is_valid_user_id(value: str) -> bool:
    return bool(_USER_ID_RE.fullmatch(value))


def require_channel_id(value: str) -> str:
    if not is_valid_channel_id(value):
        raise InvalidIdError(f"Invalid channel id: {value!r}")
    return value


def require_user_id(value: str) -> str:
    if not is_valid_user_id(value):
        raise InvalidIdError(f"Invalid user id: {value!r}")
    return value


def is_non_empty_text(value: str) -> bool:
    return bool(sanitize_text(value))


def require_text(value: str, *, max_len: int = 4000) -> str:
    text = sanitize_text(value, max_len=max_len)
    if not text:
        raise ValidationError("Text must be non-empty after sanitization")
    return text
