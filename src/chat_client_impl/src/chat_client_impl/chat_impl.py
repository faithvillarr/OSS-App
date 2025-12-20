"""Chat client implementation that adapts discord_api to chat_api."""

from typing import Any

from chat_api import ChatInterface, Message

from chat_client_impl.message_impl import ChatMessage


class ChatClient(ChatInterface):  # type: ignore[misc]
    """Chat API client implementation using Discord as the backend."""

    def __init__(
        self,
        user_id: str | None = None,
        access_token: str | None = None,
        token_type: str | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialize a chat client.

        Args:
            user_id: Optional user ID for multi-user authentication.
                     If provided, uses discord_api.get_client(user_id).
            access_token: Optional Discord access token for direct authentication.
                          If provided, creates DiscordClient directly.
            token_type: Optional token type (e.g., "Bot" or "Bearer").
                        Only used when access_token is provided.
            **kwargs: Additional keyword arguments passed to DiscordClient
                     when access_token is provided.

        """
        # Import discord_api and ensure discord_client_impl is registered
        import discord_client_impl  # noqa: F401, PLC0415

        # If access_token is provided, create DiscordClient directly
        # Otherwise, use discord_api.get_client(user_id)
        # Note: _discord_client is a discord_api.client.ChatInterface, not chat_api.ChatInterface
        # but they have compatible interfaces for our purposes
        if access_token is not None:
            from discord_client_impl.discord_impl import DiscordClient  # noqa: PLC0415

            self._discord_client = DiscordClient(  # type: ignore[assignment]
                access_token=access_token,
                token_type=token_type,
                **kwargs,  # type: ignore[arg-type]
            )
        else:
            import discord_api  # noqa: PLC0415

            self._discord_client = discord_api.get_client(user_id=user_id)  # type: ignore[assignment]

    def send_message(self, channel_id: str, content: str) -> bool:
        """Send a message to a channel.

        Args:
            channel_id: The ID of the channel to send the message to.
            content: The text content of the message.

        Returns:
            bool: True if the message was successfully sent, False otherwise.

        """
        result = self._discord_client.send_message(channel_id, content)
        return bool(result)

    def get_messages(self, channel_id: str, limit: int = 10) -> list[Message]:
        """Retrieve recent messages from a channel.

        Args:
            channel_id: The ID of the channel to retrieve messages from.
            limit: Maximum number of messages to retrieve (default: 10).

        Returns:
            list[Message]: A list of messages from the channel.

        """
        discord_messages = self._discord_client.get_messages(channel_id, limit)
        return [ChatMessage(msg) for msg in discord_messages]  # type: ignore[arg-type]

    def delete_message(self, channel_id: str, message_id: str) -> bool:
        """Delete a message from a channel.

        Args:
            channel_id: The ID of the channel containing the message.
            message_id: The ID of the message to delete.

        Returns:
            bool: True if the message was successfully deleted, False otherwise.

        """
        result = self._discord_client.delete_message(channel_id, message_id)
        return bool(result)
