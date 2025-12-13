from __future__ import annotations

from typing import Iterable, List

from slack_api import ChatClient, Channel, Message


class FakeClient:
    """A tiny in-test fake that satisfies the ChatClient Protocol."""

    def __init__(self) -> None:
        self._chans: List[Channel] = [Channel(id="C12", name="general")]

    def health(self) -> bool:
        return True

    def list_channels(self) -> Iterable[Channel]:
        return list(self._chans)

    def post_message(self, channel_id: str, text: str) -> Message:
        return Message(channel_id=channel_id, text=text, ts="20240101T000000Z")


def test_protocol_surface_and_behavior() -> None:
    client: ChatClient = FakeClient()  # type: ignore[assignment]
    assert client.health() is True
    chans = list(client.list_channels())
    assert len(chans) == 1 and chans[0].id == "C12"
    m = client.post_message("C12", "hello")
    assert m.channel_id == "C12" and m.text == "hello" and isinstance(m.ts, str)
