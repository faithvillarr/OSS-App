"""Unit tests for Discord client registration with discord_api."""

import sys

import pytest


def test_registration_overrides_get_client() -> None:
    """Test that registration overrides discord_api.get_client."""
    # Remove modules if already loaded
    for module in list(sys.modules.keys()):
        if module.startswith("discord_api") or module.startswith("discord_client_impl"):
            del sys.modules[module]

    # Import discord_api first (unregistered)
    import discord_api

    # Verify get_client raises NotImplementedError before registration
    with pytest.raises(NotImplementedError):
        discord_api.get_client()

    # Import discord_client_impl (triggers registration)
    import discord_client_impl  # noqa: F401

    # Verify get_client now works (returns DiscordClient)
    client = discord_api.get_client()
    assert client is not None
    assert hasattr(client, "get_messages")
    assert hasattr(client, "send_message")


def test_registration_overrides_get_message() -> None:
    """Test that registration overrides discord_api.get_message."""
    # Import discord_client_impl (triggers registration)
    import discord_api

    # Call get_message with Discord data
    raw_data = {
        "id": "123",
        "channel_id": "456",
        "content": "Test",
        "timestamp": "2025-01-15T10:30:00.000000+00:00",
        "author": {"id": "789", "username": "test"},
    }

    message = discord_api.get_message("123", raw_data)  # type: ignore[arg-type]

    assert message is not None
    assert message.id == "123"
    assert message.content == "Test"


def test_registration_overrides_get_channel() -> None:
    """Test that registration overrides discord_api.get_channel."""
    import discord_api

    # Call get_channel with Discord data
    raw_data = {
        "id": "123456789",
        "name": "general",
        "type": 0,
    }

    channel = discord_api.get_channel("123456789", raw_data)  # type: ignore[arg-type]

    assert channel is not None
    assert channel.channel_id == "123456789"
    assert channel.name == "general"


def test_get_client_impl_returns_discord_client() -> None:
    """Test that get_client_impl returns a DiscordClient instance."""
    from discord_client_impl import get_client_impl

    client = get_client_impl(user_id="test_user")

    assert client is not None
    # Verify it has DiscordClient methods
    assert hasattr(client, "_get_authorization_url")
    assert hasattr(client, "_exchange_code_for_token")
