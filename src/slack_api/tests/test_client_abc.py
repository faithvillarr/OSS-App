from __future__ import annotations

from typing import Iterable, List

from slack_api.client import ChatClient
from slack_api import Channel, Message


class FakeChatClient(ChatClient):
    """Concrete implementation of the ChatClient ABC for testing."""

    def __init__(self) -> None:
        self._channels: List[Channel] = [Channel(id="C123", name="general")]

    def health(self) -> bool:
        return True

    def list_channels(self) -> Iterable[Channel]:
        return list(self._channels)

    def post_message(self, channel_id: str, text: str) -> Message:
        return Message(channel_id=channel_id, text=text, ts="20240101T000000Z")


def test_chat_client_abc_concrete_impl_behaves_like_interface() -> None:
    client = FakeChatClient()

    # health()
    assert client.health() is True

    # list_channels()
    channels = list(client.list_channels())
    assert len(channels) == 1
    chan = channels[0]
    assert isinstance(chan, Channel)
    assert chan.id == "C123"
    assert chan.name == "general"

    # post_message()
    msg = client.post_message("C123", "hello")
    assert isinstance(msg, Message)
    assert msg.channel_id == "C123"
    assert msg.text == "hello"
    assert isinstance(msg.ts, str)

