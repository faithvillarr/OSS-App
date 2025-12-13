from __future__ import annotations


def test_imports_surface() -> None:
    from slack_api.client import ChatClient as _ChatClient  # noqa: F401
    from slack_api.types import Channel as _C, User as _U, Message as _M  # noqa: F401
