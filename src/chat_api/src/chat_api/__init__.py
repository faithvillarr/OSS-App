"""Abstract interfaces for Chat APIs."""

from abc import ABC, abstractmethod


class Message(ABC):
    """Abstract representation of a chat message.

    Students must implement this to wrap their platform-specific message objects.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for the message."""
        raise NotImplementedError

    @property
    @abstractmethod
    def content(self) -> str:
        """The actual text content of the message."""
        raise NotImplementedError

    @property
    @abstractmethod
    def sender_id(self) -> str:
        """The ID of the user who sent the message."""
        raise NotImplementedError

class ChatInterface(ABC):
    """A minimal interface for sending and receiving messages."""

    @abstractmethod
    def send_message(self, channel_id: str, content: str) -> bool:
        """Send a message to a specific destination (channel/thread).

        :return: True if the message was sent successfully, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def get_messages(self, channel_id: str, limit: int = 10) -> list[Message]:
        """Read the last N messages from a destination."""
        raise NotImplementedError

    @abstractmethod
    def delete_message(self, channel_id: str, message_id: str) -> bool:
        """Delete a specific message. Returns True if successful."""
        raise NotImplementedError
