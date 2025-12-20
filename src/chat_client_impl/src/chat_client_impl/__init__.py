"""Chat client implementation that adapts discord_api to chat_api.

This module provides a ChatClient implementation that uses Discord as the backend,
adapting the richer discord_api interface to the minimal chat_api contract.

Usage:
    from chat_client_impl import ChatClient

    # Create client with access token
    client = ChatClient(access_token="your_token", token_type="Bot")

    # Or use factory pattern with user_id
    client = ChatClient(user_id="user123")

    # Use the chat API interface
    client.send_message(channel_id="123", content="Hello!")
    messages = client.get_messages(channel_id="123", limit=10)
    client.delete_message(channel_id="123", message_id="456")
"""

import os

import chat_api

from chat_client_impl.chat_impl import ChatClient
from chat_client_impl.message_impl import ChatMessage

__all__ = ["ChatClient", "ChatMessage"]


def get_client(user_id: str | None = None) -> ChatClient:
    """Create a ChatClient instance.

    Args:
        user_id: Optional user ID for multi-user authentication.

    Returns:
        ChatClient: A configured chat client instance.

    """
    return ChatClient(user_id=user_id)


def get_client_impl(user_id: str | None = None) -> chat_api.ChatInterface:
    """Create a ChatClient instance for chat_api registration.

    Args:
        user_id: Optional user ID for multi-user authentication.
                 If None and DISCORD_BOT_TOKEN is set, uses bot token authentication.

    Returns:
        ChatClient: A configured chat client instance.

    """
    # Check for bot token in environment (for non-interactive/service account usage)
    bot_token = os.getenv("DISCORD_BOT_TOKEN")
    if bot_token:
        return ChatClient(access_token=bot_token, token_type="Bot")  # noqa: S106
    return ChatClient(user_id=user_id)


def register() -> None:
    """Register ChatClient implementation with chat_api.

    This function overrides the factory function in chat_api
    to return ChatClient implementations.

    """
    chat_api.get_client = get_client_impl


# Auto-register on import (side-effect import pattern)
register()
