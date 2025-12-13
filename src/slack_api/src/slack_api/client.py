from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterable
from .types import Channel, Message


class ChatClient(ABC):
    """Abstract base class for a Slack-like chat client.

    Concrete implementations (e.g., slack_impl.SlackClient, adapters)
    should subclass this and implement all abstract methods.
    """

    @abstractmethod
    def health(self) -> bool:
        """Return True if the underlying service is healthy."""
        pass

    @abstractmethod
    def list_channels(self) -> Iterable[Channel]:
        """List accessible channels."""
        pass

    @abstractmethod
    def post_message(self, channel_id: str, text: str) -> Message:
        """Post a message to a channel and return the created message."""
        pass
