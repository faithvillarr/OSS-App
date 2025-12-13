from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .errors import ValidationError
from .validators import require_channel_id, require_user_id, require_text
from .utils import sanitize_text


@dataclass(frozen=True)
class Channel:
    id: str
    name: str

    def to_dict(self) -> Dict[str, str]:
        return {"id": self.id, "name": self.name}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Channel":
        chan_id = require_channel_id(str(data["id"]))
        name_raw = str(data["name"])
        name = sanitize_text(name_raw, max_len=80)
        if not name:
            raise ValidationError("Channel.name must be non-empty")
        return cls(id=chan_id, name=name)


@dataclass(frozen=True)
class User:
    id: str
    username: str

    def to_dict(self) -> Dict[str, str]:
        return {"id": self.id, "username": self.username}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        user_id = require_user_id(str(data["id"]))
        username_raw = str(data["username"])
        username = sanitize_text(username_raw, max_len=80)
        if not username:
            raise ValidationError("User.username must be non-empty")
        return cls(id=user_id, username=username)


@dataclass(frozen=True)
class Message:
    channel_id: str
    text: str
    ts: str | None = None
    # Optional message_id to satisfy adapter tests that pass message_id=...
    message_id: str | None = None

    @property
    def id(self) -> str | None:
        """Alias for the message identifier, for backwards-compat tests."""
        return self.message_id

    def to_dict(self) -> Dict[str, str | None]:
        # Keep original wire format (no message_id) for slack_api.
        return {"channel_id": self.channel_id, "text": self.text, "ts": self.ts}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        channel_id = require_channel_id(str(data["channel_id"]))
        text = require_text(str(data["text"]))  # validates + non-empty after sanitize
        ts_val = data.get("ts")
        ts = None if ts_val is None else str(ts_val)
        # We intentionally ignore any message_id in `data` to keep the original
        # contract; callers that care can set it manually.
        return cls(channel_id=channel_id, text=text, ts=ts)
