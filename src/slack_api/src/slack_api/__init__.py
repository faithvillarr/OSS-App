# src/slack_api/src/slack_api/__init__.py
from __future__ import annotations

from .client import ChatClient
from .errors import InvalidIdError, ValidationError
from .types import Channel, Message, User
from .utils import sanitize_text, utc_ts
from .validators import (
    is_non_empty_text,
    is_valid_channel_id,
    is_valid_user_id,
    require_channel_id,
    require_text,
    require_user_id,
)

# Explicit public API (sorted for Ruff RUF022)
__all__ = [
    "Channel",
    "ChatClient",
    "InvalidIdError",
    "Message",
    "User",
    "ValidationError",
    "is_non_empty_text",
    "is_valid_channel_id",
    "is_valid_user_id",
    "require_channel_id",
    "require_text",
    "require_user_id",
    "sanitize_text",
    "utc_ts",
]