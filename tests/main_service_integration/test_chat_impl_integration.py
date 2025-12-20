"""Integration tests for ChatClient implementation.

Tests verify that ChatClient methods are correctly used,
increasing coverage of chat_impl.py by testing various initialization paths and methods.

Improve coverage for chat_impl.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from main_service.main import (
    _determine_bot_user_id,
    _filter_new_messages,
    _initialize_seen_messages,
    _process_new_message,
)

pytestmark = pytest.mark.integration


class TestChatClientInitialization:
    """Test ChatClient initialization paths."""

    def test_chat_client_init_with_access_token(
        self,
    ) -> None:
        """Test ChatClient initialization with access_token (lines 36-43)."""
        from chat_client_impl.chat_impl import ChatClient

        # Mock DiscordClient import - patch where it's imported in chat_impl
        with patch("discord_client_impl.DiscordClient") as mock_discord_class:
            mock_discord_client = MagicMock()
            mock_discord_class.return_value = mock_discord_client

            client = ChatClient(access_token="test_token", token_type="Bot")

            # Verify DiscordClient was created with access_token
            mock_discord_class.assert_called_once_with(
                access_token="test_token", token_type="Bot"
            )
            assert client._discord_client is mock_discord_client

    def test_chat_client_init_with_user_id(
        self,
    ) -> None:
        """Test ChatClient initialization with user_id (lines 44-47)."""
        from chat_client_impl.chat_impl import ChatClient

        import discord_api

        # Mock discord_api.get_client
        with patch.object(discord_api, "get_client") as mock_get_client:
            mock_discord_client = MagicMock()
            mock_get_client.return_value = mock_discord_client

            client = ChatClient(user_id="user_123")

            # Verify discord_api.get_client was called
            mock_get_client.assert_called_once_with(user_id="user_123")
            assert client._discord_client is mock_discord_client

    def test_chat_client_init_without_params(
        self,
    ) -> None:
        """Test ChatClient initialization without parameters (uses discord_api.get_client)."""
        from chat_client_impl.chat_impl import ChatClient

        import discord_api

        # Mock discord_api.get_client
        with patch.object(discord_api, "get_client") as mock_get_client:
            mock_discord_client = MagicMock()
            mock_get_client.return_value = mock_discord_client

            client = ChatClient()

            # Verify discord_api.get_client was called without user_id
            mock_get_client.assert_called_once_with(user_id=None)
            assert client._discord_client is mock_discord_client

    def test_chat_client_init_with_kwargs(
        self,
    ) -> None:
        """Test ChatClient initialization with additional kwargs."""
        from chat_client_impl.chat_impl import ChatClient

        # Mock DiscordClient import - patch where it's imported in chat_impl
        with patch("discord_client_impl.DiscordClient") as mock_discord_class:
            mock_discord_client = MagicMock()
            mock_discord_class.return_value = mock_discord_client

            ChatClient(
                access_token="test_token",
                token_type="Bot",
                client_id="client_123",
                redirect_uri="http://localhost/callback",
            )

            # Verify DiscordClient was created with all kwargs
            mock_discord_class.assert_called_once_with(
                access_token="test_token",
                token_type="Bot",
                client_id="client_123",
                redirect_uri="http://localhost/callback",
            )


class TestChatClientMethods:
    """Test ChatClient methods."""

    def test_send_message(
        self,
    ) -> None:
        """Test send_message method (line 60)."""
        from chat_client_impl.chat_impl import ChatClient

        # Create client with mocked DiscordClient
        mock_discord_client = MagicMock()
        mock_discord_client.send_message.return_value = True

        client = ChatClient(access_token="test_token")
        client._discord_client = mock_discord_client

        result = client.send_message("channel_123", "Test message")

        assert result is True
        mock_discord_client.send_message.assert_called_once_with("channel_123", "Test message")

    def test_get_messages(
        self,
    ) -> None:
        """Test get_messages method with message conversion (lines 73-74)."""
        from chat_client_impl.chat_impl import ChatClient
        from discord_client_impl.message_impl import DiscordMessage

        # Create Discord messages
        msg1_data = {
            "id": "msg_1",
            "channel_id": "channel_123",
            "content": "Message 1",
            "author": {"id": "user_1", "username": "user1"},
            "timestamp": "2024-01-01T00:00:00.000000+00:00",
            "edited_timestamp": None,
        }
        discord_msg1 = DiscordMessage(msg1_data)

        msg2_data = {
            "id": "msg_2",
            "channel_id": "channel_123",
            "content": "Message 2",
            "author": {"id": "user_2", "username": "user2"},
            "timestamp": "2024-01-01T00:01:00.000000+00:00",
            "edited_timestamp": None,
        }
        discord_msg2 = DiscordMessage(msg2_data)

        # Create client with mocked DiscordClient
        mock_discord_client = MagicMock()
        mock_discord_client.get_messages.return_value = [discord_msg1, discord_msg2]

        client = ChatClient(access_token="test_token")
        client._discord_client = mock_discord_client

        messages = client.get_messages("channel_123", limit=10)

        # Verify messages were converted to ChatMessage
        assert len(messages) == 2  # noqa: PLR2004
        from chat_client_impl.message_impl import ChatMessage

        assert isinstance(messages[0], ChatMessage)
        assert isinstance(messages[1], ChatMessage)
        assert messages[0].id == "msg_1"
        assert messages[1].id == "msg_2"
        mock_discord_client.get_messages.assert_called_once_with("channel_123", 10)

    def test_get_messages_empty_list(
        self,
    ) -> None:
        """Test get_messages with empty list."""
        from chat_client_impl.chat_impl import ChatClient

        # Create client with mocked DiscordClient
        mock_discord_client = MagicMock()
        mock_discord_client.get_messages.return_value = []

        client = ChatClient(access_token="test_token")
        client._discord_client = mock_discord_client

        messages = client.get_messages("channel_123", limit=5)

        assert len(messages) == 0
        mock_discord_client.get_messages.assert_called_once_with("channel_123", 5)

    def test_delete_message(
        self,
    ) -> None:
        """Test delete_message method (line 87)."""
        from chat_client_impl.chat_impl import ChatClient

        # Create client with mocked DiscordClient
        mock_discord_client = MagicMock()
        mock_discord_client.delete_message.return_value = True

        client = ChatClient(access_token="test_token")
        client._discord_client = mock_discord_client

        result = client.delete_message("channel_123", "msg_123")

        assert result is True
        mock_discord_client.delete_message.assert_called_once_with("channel_123", "msg_123")

    def test_delete_message_failure(
        self,
    ) -> None:
        """Test delete_message returns False on failure."""
        from chat_client_impl.chat_impl import ChatClient

        # Create client with mocked DiscordClient
        mock_discord_client = MagicMock()
        mock_discord_client.delete_message.return_value = False

        client = ChatClient(access_token="test_token")
        client._discord_client = mock_discord_client

        result = client.delete_message("channel_123", "msg_123")

        assert result is False


class TestChatClientThroughMainService:
    """Test ChatClient methods through main_service integration."""

    def test_chat_client_used_through_chat_api(
        self,
    ) -> None:
        """Test that ChatClient is used when chat_api.get_client is called."""
        from chat_client_impl.chat_impl import ChatClient

        import chat_api

        # chat_client_impl should be registered, so get_client returns ChatClient
        client = chat_api.get_client()

        assert isinstance(client, ChatClient)

    def test_send_message_through_main_service(
        self,
        mock_chat_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test send_message is called through main_service."""
        from chat_client_impl.message_impl import ChatMessage

        # Mock message
        msg = ChatMessage(
            MagicMock(
                id="msg_123",
                content="Create a ticket",
                sender_id="user_123",
            )
        )

        mock_chat_client.send_message.return_value = True

        # Mock AI to return no commands
        with patch("main_service.routing.ai_api.get_client") as mock_get_client:
            mock_ai_client = MagicMock()
            mock_ai_client.generate_response.return_value = "I understand your request."
            mock_get_client.return_value = mock_ai_client

            seen_message_ids: set[str] = set()
            _process_new_message(
                client=mock_chat_client,
                msg=msg,
                channel_id="channel_123",
                seen_message_ids=seen_message_ids,
                ticket_client=mock_tickets_client,
            )

            # Verify send_message was called
            assert mock_chat_client.send_message.called

    def test_get_messages_through_main_service(
        self,
        mock_chat_client: MagicMock,
    ) -> None:
        """Test get_messages is called through main_service."""
        from chat_client_impl.message_impl import ChatMessage

        # Mock messages
        msg1 = ChatMessage(
            MagicMock(
                id="msg_1",
                content="Message 1",
                sender_id="user_1",
            )
        )
        msg2 = ChatMessage(
            MagicMock(
                id="msg_2",
                content="Message 2",
                sender_id="user_2",
            )
        )

        mock_chat_client.get_messages.return_value = [msg1, msg2]

        # Test through main_service
        seen = _initialize_seen_messages(mock_chat_client, "channel_123")

        assert "msg_1" in seen
        assert "msg_2" in seen
        mock_chat_client.get_messages.assert_called_once()

    def test_delete_message_through_main_service(
        self,
        mock_chat_client: MagicMock,
    ) -> None:
        """Test delete_message is called through main_service."""
        from chat_client_impl.message_impl import ChatMessage

        # Mock test message
        test_msg = ChatMessage(
            MagicMock(
                id="test_msg",
                content="___BOT_ID_TEST___",
                sender_id="bot_123",
            )
        )

        mock_chat_client.send_message.return_value = True
        mock_chat_client.get_messages.return_value = [test_msg]
        mock_chat_client.delete_message.return_value = True

        # Test through _determine_bot_user_id
        bot_id = _determine_bot_user_id(mock_chat_client, "channel_123")

        assert bot_id == "bot_123"
        mock_chat_client.delete_message.assert_called_once()

    def test_filter_messages_uses_chat_client_messages(
        self,
    ) -> None:
        """Test _filter_new_messages works with ChatMessage objects."""
        from chat_client_impl.message_impl import ChatMessage

        # Create ChatMessage objects
        msg1 = ChatMessage(
            MagicMock(
                id="msg_1",
                content="User message",
                sender_id="user_123",
            )
        )
        msg2 = ChatMessage(
            MagicMock(
                id="msg_2",
                content="Bot message",
                sender_id="bot_123",
            )
        )

        messages = [msg1, msg2]
        seen_ids: set[str] = set()
        bot_user_id = "bot_123"

        filtered = _filter_new_messages(messages, seen_ids, bot_user_id)

        assert len(filtered) == 1
        assert filtered[0].id == "msg_1"


class TestChatClientRegistration:
    """Test ChatClient registration with chat_api."""

    def test_chat_client_registration(
        self,
    ) -> None:
        """Test that ChatClient is registered with chat_api."""
        import chat_api

        # chat_client_impl should auto-register on import
        # So get_client should return ChatClient
        client = chat_api.get_client()

        from chat_client_impl.chat_impl import ChatClient

        assert isinstance(client, ChatClient)

    def test_get_client_impl_with_bot_token(
        self,
    ) -> None:
        """Test get_client_impl uses DISCORD_BOT_TOKEN when available."""
        import os

        from chat_client_impl import get_client_impl

        with (
            patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "bot_token_123"}),
            patch("discord_client_impl.DiscordClient") as mock_discord_class,
        ):
            # Patch DiscordClient where it's imported in chat_impl
            mock_discord_client = MagicMock()
            mock_discord_class.return_value = mock_discord_client

            client = get_client_impl()

            # Verify ChatClient was created with bot token
            mock_discord_class.assert_called_once_with(
                access_token="bot_token_123", token_type="Bot"
            )
            assert client._discord_client is mock_discord_client

    def test_get_client_impl_without_bot_token(
        self,
    ) -> None:
        """Test get_client_impl uses user_id when DISCORD_BOT_TOKEN not available."""
        import os

        import discord_api
        from chat_client_impl import get_client_impl

        with patch.dict(os.environ, {}, clear=True), patch.object(discord_api, "get_client") as mock_get_client:
            mock_discord_client = MagicMock()
            mock_get_client.return_value = mock_discord_client

            client = get_client_impl(user_id="user_123")

            # Verify discord_api.get_client was called
            mock_get_client.assert_called_once_with(user_id="user_123")
            assert client._discord_client is mock_discord_client


@pytest.fixture
def mock_chat_client() -> MagicMock:
    """Mock ChatClient for testing."""
    from chat_client_impl.chat_impl import ChatClient

    mock_client = MagicMock(spec=ChatClient)
    mock_client.send_message.return_value = True
    mock_client.get_messages.return_value = []
    mock_client.delete_message.return_value = True
    return mock_client


@pytest.fixture
def mock_tickets_client() -> MagicMock:
    """Mock TicketsClient for testing."""
    from tickets_api import Ticket, TicketStatus
    from tickets_client_impl import TicketsClient

    mock_client = MagicMock(spec=TicketsClient)

    mock_ticket = MagicMock(spec=Ticket)
    mock_ticket.id = "test_ticket_123"
    mock_ticket.title = "Test Ticket"
    mock_ticket.description = "Test Description"
    mock_ticket.status = TicketStatus.OPEN
    mock_ticket.assignee = None

    mock_client.create_ticket.return_value = mock_ticket
    mock_client.get_ticket.return_value = mock_ticket
    mock_client.search_tickets.return_value = [mock_ticket]
    mock_client.update_ticket.return_value = mock_ticket
    mock_client.delete_ticket.return_value = True

    return mock_client

