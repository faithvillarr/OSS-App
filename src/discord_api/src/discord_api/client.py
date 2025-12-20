"""Core chat client contract definitions and factory placeholder."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from discord_api.message import Channel, Message

__all__ = ["ChatInterface", "get_client"]


class ChatInterface(ABC):
    """Abstract base class representing a chat client for messaging operations."""

    @abstractmethod
    def get_message(self, channel_id: str, message_id: str) -> Message:
        """Retrieve a specific message from a channel.

        Args:
            channel_id: The ID of the channel containing the message.
            message_id: The ID of the message to retrieve.

        Returns:
            Message: The requested message.

        Raises:
            ValueError: If the message is not found.

        """
        raise NotImplementedError

    @abstractmethod
    def get_messages(self, channel_id: str, limit: int = 10) -> list[Message]:
        """Retrieve recent messages from a channel.

        Args:
            channel_id: The ID of the channel to retrieve messages from.
            limit: Maximum number of messages to retrieve (default: 10).

        Returns:
            list[Message]: An iterator of messages from the channel.

        """
        raise NotImplementedError

    @abstractmethod
    def send_message(self, channel_id: str, content: str) -> bool:
        """Send a message to a channel.

        Args:
            channel_id: The ID of the channel to send the message to.
            content: The text content of the message.

        Returns:
            bool: True if the message was successfully sent, False otherwise.

        """
        raise NotImplementedError

    @abstractmethod
    def delete_message(self, channel_id: str, message_id: str) -> bool:
        """Delete a message from a channel.

        Args:
            channel_id: The ID of the channel containing the message.
            message_id: The ID of the message to delete.

        Returns:
            bool: True if the message was successfully deleted, False otherwise.

        """
        raise NotImplementedError

    @abstractmethod
    def get_channels(self) -> Iterator[Channel]:
        """Retrieve all accessible channels.

        Returns:
            Iterator[Channel]: An iterator of available channels.

        """
        raise NotImplementedError

    @abstractmethod
    def get_channel(self, channel_id: str) -> Channel:
        """Retrieve information about a specific channel.

        Args:
            channel_id: The ID of the channel to retrieve.

        Returns:
            Channel: The requested channel.

        Raises:
            ValueError: If the channel is not found.

        """
        raise NotImplementedError


def get_client(user_id: str | None = None) -> ChatInterface:
    """Return an instance of a ChatInterface.

    Args:
        user_id: Optional user ID for multi-user authentication.
                 If None, uses a default/service account.

    Returns:
        ChatInterface: An instance conforming to the ChatInterface contract.

    Raises:
        NotImplementedError: If the function is not overridden by an implementation.

    """
    raise NotImplementedError
