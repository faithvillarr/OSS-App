"""Unit tests for Discord message and channel implementations."""

from discord_client_impl.message_impl import DiscordChannel, DiscordMessage


def test_discord_message_basic_properties() -> None:
    """Test basic Discord message properties."""
    raw_data = {
        "id": "123456789",
        "channel_id": "987654321",
        "content": "Hello, world!",
        "timestamp": "2025-01-15T10:30:00.000000+00:00",
        "edited_timestamp": None,
        "author": {
            "id": "111222333",
            "username": "testuser",
            "global_name": "Test User",
        },
    }

    message = DiscordMessage(raw_data)

    assert message.id == "123456789"
    assert message.channel_id == "987654321"
    assert message.sender_id == "111222333"
    assert message.sender_name == "Test User"
    assert message.content == "Hello, world!"
    assert message.timestamp == "2025-01-15T10:30:00.000000+00:00"
    assert message.edited_timestamp is None


def test_discord_message_edited() -> None:
    """Test Discord message with edit timestamp."""
    raw_data = {
        "id": "123",
        "channel_id": "456",
        "content": "Edited message",
        "timestamp": "2025-01-15T10:30:00.000000+00:00",
        "edited_timestamp": "2025-01-15T10:35:00.000000+00:00",
        "author": {
            "id": "789",
            "username": "editor",
        },
    }

    message = DiscordMessage(raw_data)

    assert message.edited_timestamp == "2025-01-15T10:35:00.000000+00:00"


def test_discord_message_author_fallback() -> None:
    """Test Discord message with username fallback (no global_name)."""
    raw_data = {
        "id": "123",
        "channel_id": "456",
        "content": "Test",
        "timestamp": "2025-01-15T10:30:00.000000+00:00",
        "edited_timestamp": None,
        "author": {
            "id": "789",
            "username": "fallback_user",
        },
    }

    message = DiscordMessage(raw_data)

    assert message.sender_name == "fallback_user"


def test_discord_message_missing_author() -> None:
    """Test Discord message with missing author data."""
    raw_data = {
        "id": "123",
        "channel_id": "456",
        "content": "Test",
        "timestamp": "2025-01-15T10:30:00.000000+00:00",
    }

    message = DiscordMessage(raw_data)

    assert message.sender_id == ""
    assert message.sender_name == "Unknown"


def test_discord_channel_basic_properties() -> None:
    """Test basic Discord channel properties."""
    raw_data = {
        "id": "123456789",
        "name": "general",
        "type": 0,  # GUILD_TEXT
    }

    channel = DiscordChannel(raw_data)

    assert channel.channel_id == "123456789"
    assert channel.name == "general"
    assert channel.channel_type == "text"


def test_discord_channel_dm() -> None:
    """Test Discord DM channel."""
    raw_data = {
        "id": "123456789",
        "type": 1,  # DM
        "recipients": [
            {"username": "alice"},
            {"username": "bob"},
        ],
    }

    channel = DiscordChannel(raw_data)

    assert channel.channel_id == "123456789"
    assert "alice" in channel.name
    assert "bob" in channel.name
    assert channel.channel_type == "dm"


def test_discord_channel_voice() -> None:
    """Test Discord voice channel."""
    raw_data = {
        "id": "987654321",
        "name": "Voice Channel",
        "type": 2,  # GUILD_VOICE
    }

    channel = DiscordChannel(raw_data)

    assert channel.channel_type == "voice"


def test_discord_channel_unknown_type() -> None:
    """Test Discord channel with unknown type."""
    raw_data = {
        "id": "111222333",
        "name": "Unknown",
        "type": 999,  # Unknown type
    }

    channel = DiscordChannel(raw_data)

    assert channel.channel_type == "unknown_999"


def test_discord_channel_dm_without_recipients() -> None:
    """Test Discord DM channel without recipients data."""
    raw_data = {
        "id": "123456789",
        "type": 1,  # DM
        "recipients": [],  # Empty recipients list
    }

    channel = DiscordChannel(raw_data)

    assert channel.name == "Direct Message"
    assert channel.channel_type == "dm"
