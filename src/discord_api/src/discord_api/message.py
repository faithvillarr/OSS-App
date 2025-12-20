"""Message contract - Core chat message representation."""

from abc import ABC, abstractmethod


class Message(ABC):
    """Abstract base class representing a chat message."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Return the unique identifier of the message."""
        raise NotImplementedError

    @property
    @abstractmethod
    def channel_id(self) -> str:
        """Return the ID of the channel where the message was sent."""
        raise NotImplementedError

    @property
    @abstractmethod
    def sender_id(self) -> str:
        """Return the ID of the message author."""
        raise NotImplementedError

    @property
    @abstractmethod
    def sender_name(self) -> str:
        """Return the display name of the message author."""
        raise NotImplementedError

    @property
    @abstractmethod
    def content(self) -> str:
        """Return the text content of the message."""
        raise NotImplementedError

    @property
    @abstractmethod
    def timestamp(self) -> str:
        """Return the timestamp when the message was created (ISO 8601 format)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def edited_timestamp(self) -> str | None:
        """Return the timestamp when the message was last edited, or None if never edited."""
        raise NotImplementedError


class Channel(ABC):
    """Abstract base class representing a chat channel."""

    @property
    @abstractmethod
    def channel_id(self) -> str:
        """Return the unique identifier of the channel."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the channel."""
        raise NotImplementedError

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """Return the type of channel (e.g., 'text', 'voice', 'dm')."""
        raise NotImplementedError


def get_message(msg_id: str, raw_data: dict[str, str]) -> Message:
    """Return an instance of a Message.

    Args:
        msg_id: The unique identifier for the message.
        raw_data: Dictionary containing raw message data from the chat platform.

    Returns:
        Message: An instance conforming to the Message contract.

    Raises:
        NotImplementedError: If the function is not overridden by an implementation.

    """
    raise NotImplementedError


def get_channel(channel_id: str, raw_data: dict[str, str]) -> Channel:
    """Return an instance of a Channel.

    Args:
        channel_id: The unique identifier for the channel.
        raw_data: Dictionary containing raw channel data from the chat platform.

    Returns:
        Channel: An instance conforming to the Channel contract.

    Raises:
        NotImplementedError: If the function is not overridden by an implementation.

    """
    raise NotImplementedError
