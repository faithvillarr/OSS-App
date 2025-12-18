"""Chat message implementation that adapts discord_api.Message to chat_api.Message."""

from chat_api import Message
from discord_api.message import Message as DiscordMessage


class ChatMessage(Message):
    """Chat API message implementation that wraps a discord_api.Message."""

    def __init__(self, discord_message: DiscordMessage) -> None:
        """Initialize a chat message from a Discord message.

        Args:
            discord_message: The Discord message to wrap.

        """
        self._discord_message = discord_message

    @property
    def id(self) -> str:
        """Return the unique identifier of the message."""
        return self._discord_message.id

    @property
    def content(self) -> str:
        """Return the text content of the message."""
        return self._discord_message.content

    @property
    def sender_id(self) -> str:
        """Return the ID of the message author."""
        return self._discord_message.sender_id
