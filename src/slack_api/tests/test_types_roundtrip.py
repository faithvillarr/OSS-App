from __future__ import annotations

import pytest

from slack_api import Channel, User, Message, ValidationError


def test_channel_roundtrip_normalizes() -> None:
    c = Channel.from_dict({"id": "C123", "name": "  general "})
    assert c.to_dict() == {"id": "C123", "name": "general"}


def test_user_roundtrip_normalizes() -> None:
    u = User.from_dict({"id": "U42", "username": "  alice  "})
    assert u.to_dict() == {"id": "U42", "username": "alice"}


def test_message_roundtrip_and_validation() -> None:
    m = Message.from_dict(
        {"channel_id": "C123", "text": "  hi   there  ", "ts": "1.23"}
    )
    assert m.to_dict() == {"channel_id": "C123", "text": "hi there", "ts": "1.23"}

    with pytest.raises(ValidationError):
        Message.from_dict({"channel_id": "C123", "text": "   \n\t  "})
