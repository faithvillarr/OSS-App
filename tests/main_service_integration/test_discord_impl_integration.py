"""Integration tests for DiscordClient implementation.

Tests verify that DiscordClient methods are correctly used,
increasing coverage of discord_impl.py by testing various success and error paths.

Improve coverage for discord_impl.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
import pytest
from discord_api.exceptions import (
    AuthenticationError,
    ChannelNotFoundError,
    MessageDeleteError,
    MessageNotFoundError,
    MessageSendError,
)
from main_service.main import (
    _determine_bot_user_id,
    _filter_new_messages,
    _initialize_seen_messages,
    _process_new_message,
)

if TYPE_CHECKING:
    import chat_api

pytestmark = pytest.mark.integration


class TestDiscordClientDirectMethods:
    """Test DiscordClient methods directly."""

    def test_discord_client_init_with_access_token(
        self,
    ) -> None:
        """Test DiscordClient initialization with access token."""
        from discord_client_impl.discord_impl import DiscordClient

        # Initialize with access token
        client = DiscordClient(access_token="test_token", token_type="Bot")

        assert client.access_token == "test_token"
        assert client.token_type == "Bot"
        assert client._http_client is not None

    def test_discord_client_init_without_token(
        self,
    ) -> None:
        """Test DiscordClient initialization without token."""
        from discord_client_impl.discord_impl import DiscordClient

        # Initialize without token
        client = DiscordClient()

        assert client.access_token is None
        assert client._http_client is not None

    def test_discord_client_init_with_env_vars(
        self,
    ) -> None:
        """Test DiscordClient initialization with environment variables."""
        import os

        from discord_client_impl.discord_impl import DiscordClient

        with patch.dict(os.environ, {"DISCORD_CLIENT_ID": "env_client_id"}):
            client = DiscordClient()

            assert client.client_id == "env_client_id"

    def test_get_authorization_url(
        self,
    ) -> None:
        """Test _get_authorization_url method."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="http://localhost:8001/callback",
        )

        url, state = client._get_authorization_url()

        assert "discord.com" in url
        assert "test_client_id" in url
        assert state is not None

    def test_get_authorization_url_with_state(
        self,
    ) -> None:
        """Test _get_authorization_url with custom state."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(
            client_id="test_client_id",
            client_secret="test_secret",
        )

        _url, state = client._get_authorization_url(state="custom_state")

        assert state == "custom_state"

    def test_exchange_code_for_token(
        self,
    ) -> None:
        """Test _exchange_code_for_token method."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="http://localhost:8001/callback",
        )

        # Mock OAuth2Client
        with patch("discord_client_impl.discord_impl.OAuth2Client") as mock_oauth:
            mock_client = MagicMock()
            mock_client.fetch_token.return_value = {
                "access_token": "new_token",
                "token_type": "Bearer",
                "refresh_token": "refresh_token",
                "expires_in": 3600,
            }
            mock_oauth.return_value = mock_client

            result = client._exchange_code_for_token("auth_code")

            assert result["access_token"] == "new_token"
            assert client.access_token == "new_token"

    def test_exchange_code_for_token_error(
        self,
    ) -> None:
        """Test _exchange_code_for_token handles errors."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="http://localhost:8001/callback",
        )

        # Mock OAuth2Client to raise error
        with patch("discord_client_impl.discord_impl.OAuth2Client") as mock_oauth:
            mock_client = MagicMock()
            mock_client.fetch_token.side_effect = Exception("Token exchange failed")
            mock_oauth.return_value = mock_client

            with pytest.raises(ValueError, match="Token exchange failed"):
                client._exchange_code_for_token("auth_code")

    def test_refresh_token(
        self,
    ) -> None:
        """Test _refresh_access_token method."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(
            client_id="test_client_id",
            client_secret="test_secret",
        )

        # Mock OAuth2Client
        with patch("discord_client_impl.discord_impl.OAuth2Client") as mock_oauth:
            mock_client = MagicMock()
            mock_client.refresh_token.return_value = {
                "access_token": "refreshed_token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
            mock_oauth.return_value = mock_client

            result = client._refresh_access_token("refresh_token")

            assert result["access_token"] == "refreshed_token"
            assert client.access_token == "refreshed_token"

    def test_refresh_token_error(
        self,
    ) -> None:
        """Test _refresh_access_token handles errors."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(
            client_id="test_client_id",
            client_secret="test_secret",
        )

        # Mock OAuth2Client to raise error
        with patch("discord_client_impl.discord_impl.OAuth2Client") as mock_oauth:
            mock_client = MagicMock()
            mock_client.refresh_token.side_effect = Exception("Token refresh failed")
            mock_oauth.return_value = mock_client

            with pytest.raises(ValueError, match="Token refresh failed"):
                client._refresh_access_token("refresh_token")

    def test_update_http_client(
        self,
    ) -> None:
        """Test _update_http_client method."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="old_token", token_type="Bot")
        old_client = client._http_client

        # Update token and HTTP client
        client.access_token = "new_token"
        client._update_http_client()

        # Verify old client was closed and new one created
        assert client._http_client is not old_client
        assert client.access_token == "new_token"

    def test_ensure_authenticated_success(
        self,
    ) -> None:
        """Test _ensure_authenticated when authenticated."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Should not raise
        client._ensure_authenticated()

    def test_ensure_authenticated_failure(
        self,
    ) -> None:
        """Test _ensure_authenticated raises error when not authenticated."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient()

        with pytest.raises(AuthenticationError):
            client._ensure_authenticated()

    def test_get_message_success(
        self,
    ) -> None:
        """Test get_message success path."""
        from discord_client_impl.discord_impl import DiscordClient
        from discord_client_impl.message_impl import DiscordMessage

        client = DiscordClient(access_token="test_token")

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "msg_123",
            "channel_id": "channel_123",
            "content": "Test message",
            "author": {"id": "user_123", "username": "testuser"},
            "timestamp": "2024-01-01T00:00:00.000000+00:00",
            "edited_timestamp": None,
        }
        mock_response.raise_for_status.return_value = None

        with patch.object(client._http_client, "get", return_value=mock_response):
            message = client.get_message("channel_123", "msg_123")

            assert isinstance(message, DiscordMessage)
            assert message.id == "msg_123"

    def test_get_message_not_found(
        self,
    ) -> None:
        """Test get_message handles 404 error."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP 404 error
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)

        with (
            patch.object(client._http_client, "get", side_effect=http_error),
            pytest.raises(MessageNotFoundError),
        ):
            client.get_message("channel_123", "nonexistent")

    def test_get_message_other_error(
        self,
    ) -> None:
        """Test get_message handles other HTTP errors."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP 500 error
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = httpx.HTTPStatusError("Internal Server Error", request=MagicMock(), response=mock_response)

        with (
            patch.object(client._http_client, "get", side_effect=http_error),
            pytest.raises(MessageNotFoundError),
        ):
            client.get_message("channel_123", "msg_123")

    def test_get_message_generic_exception(
        self,
    ) -> None:
        """Test get_message handles generic exceptions."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock generic exception
        network_error = RuntimeError("Network error")
        with (
            patch.object(client._http_client, "get", side_effect=network_error),
            pytest.raises(MessageNotFoundError),
        ):
            client.get_message("channel_123", "msg_123")

    def test_get_messages_success(
        self,
    ) -> None:
        """Test get_messages success path."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "msg_1",
                "channel_id": "channel_123",
                "content": "Message 1",
                "author": {"id": "user_1", "username": "user1"},
                "timestamp": "2024-01-01T00:00:00.000000+00:00",
            },
            {
                "id": "msg_2",
                "channel_id": "channel_123",
                "content": "Message 2",
                "author": {"id": "user_2", "username": "user2"},
                "timestamp": "2024-01-01T00:01:00.000000+00:00",
            },
        ]
        mock_response.raise_for_status.return_value = None

        with patch.object(client._http_client, "get", return_value=mock_response):
            messages = client.get_messages("channel_123", limit=10)

            assert len(messages) == 2  # noqa: PLR2004
            assert messages[0].id == "msg_1"
            assert messages[1].id == "msg_2"

    def test_get_messages_limit_capped(
        self,
    ) -> None:
        """Test get_messages caps limit at 100."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None

        with patch.object(client._http_client, "get", return_value=mock_response) as mock_get:
            client.get_messages("channel_123", limit=200)

            # Verify limit was capped at 100
            call_args = mock_get.call_args
            assert call_args[1]["params"]["limit"] == 100  # noqa: PLR2004

    def test_get_messages_error(
        self,
    ) -> None:
        """Test get_messages handles errors."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = httpx.HTTPStatusError("Internal Server Error", request=MagicMock(), response=mock_response)

        with (
            patch.object(client._http_client, "get", side_effect=http_error),
            pytest.raises(ValueError, match=r".*"),
        ):
            client.get_messages("channel_123", limit=10)

    def test_get_messages_generic_exception(
        self,
    ) -> None:
        """Test get_messages handles generic exceptions."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock generic exception
        with (
            patch.object(client._http_client, "get", side_effect=Exception("Network error")),
            pytest.raises(ValueError, match=r".*"),
        ):
            client.get_messages("channel_123", limit=10)

    def test_send_message_success(
        self,
    ) -> None:
        """Test send_message success path."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        with patch.object(client._http_client, "post", return_value=mock_response):
            result = client.send_message("channel_123", "Test message")

            assert result is True

    def test_send_message_empty_content(
        self,
    ) -> None:
        """Test send_message raises error for empty content."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        with pytest.raises(MessageSendError, match="cannot be empty"):
            client.send_message("channel_123", "")

    def test_send_message_whitespace_content(
        self,
    ) -> None:
        """Test send_message raises error for whitespace-only content."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        with pytest.raises(MessageSendError, match="cannot be empty"):
            client.send_message("channel_123", "   ")

    def test_send_message_generic_error(
        self,
    ) -> None:
        """Test send_message handles generic exceptions."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP client to raise generic exception
        network_error = RuntimeError("Network error")
        with (
            patch.object(client._http_client, "post", side_effect=network_error),
            pytest.raises(MessageSendError),
        ):
            client.send_message("channel_123", "Test message")

    def test_send_message_error(
        self,
    ) -> None:
        """Test send_message handles errors."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 403
        http_error = httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=mock_response)

        with (
            patch.object(client._http_client, "post", side_effect=http_error),
            pytest.raises(MessageSendError),
        ):
            client.send_message("channel_123", "Test message")

    def test_delete_message_success(
        self,
    ) -> None:
        """Test delete_message success path."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status.return_value = None

        with patch.object(client._http_client, "delete", return_value=mock_response):
            result = client.delete_message("channel_123", "msg_123")

            assert result is True

    def test_delete_message_not_found(
        self,
    ) -> None:
        """Test delete_message handles 404 error."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP 404 error
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)

        with (
            patch.object(client._http_client, "delete", side_effect=http_error),
            pytest.raises(MessageNotFoundError),
        ):
            client.delete_message("channel_123", "nonexistent")

    def test_delete_message_other_error(
        self,
    ) -> None:
        """Test delete_message handles other errors."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP 500 error
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = httpx.HTTPStatusError("Internal Server Error", request=MagicMock(), response=mock_response)

        with (
            patch.object(client._http_client, "delete", side_effect=http_error),
            pytest.raises(MessageDeleteError),
        ):
            client.delete_message("channel_123", "msg_123")

    def test_delete_message_generic_exception(
        self,
    ) -> None:
        """Test delete_message handles generic exceptions."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock generic exception
        network_error = RuntimeError("Network error")
        with (
            patch.object(client._http_client, "delete", side_effect=network_error),
            pytest.raises(MessageDeleteError),
        ):
            client.delete_message("channel_123", "msg_123")

    def test_get_channels_success(
        self,
    ) -> None:
        """Test get_channels success path."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "channel_1",
                "type": 1,
                "recipients": [{"id": "user_1", "username": "user1"}],
            },
            {"id": "channel_2", "type": 0, "name": "test-channel"},
        ]
        mock_response.raise_for_status.return_value = None

        with patch.object(client._http_client, "get", return_value=mock_response):
            channels = list(client.get_channels())

            assert len(channels) == 2  # noqa: PLR2004

    def test_get_channels_error(
        self,
    ) -> None:
        """Test get_channels handles errors."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = httpx.HTTPStatusError("Internal Server Error", request=MagicMock(), response=mock_response)

        with (
            patch.object(client._http_client, "get", side_effect=http_error),
            pytest.raises(ValueError, match=r".*"),
        ):
            list(client.get_channels())

    def test_get_channels_generic_exception(
        self,
    ) -> None:
        """Test get_channels handles generic exceptions."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock generic exception
        with (
            patch.object(client._http_client, "get", side_effect=Exception("Network error")),
            pytest.raises(ValueError, match=r".*"),
        ):
            list(client.get_channels())

    def test_get_channel_success(
        self,
    ) -> None:
        """Test get_channel success path."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "channel_123",
            "name": "test-channel",
            "type": 0,
        }
        mock_response.raise_for_status.return_value = None

        with patch.object(client._http_client, "get", return_value=mock_response):
            channel = client.get_channel("channel_123")

            assert channel.channel_id == "channel_123"
            assert channel.name == "test-channel"

    def test_get_channel_not_found(
        self,
    ) -> None:
        """Test get_channel handles 404 error."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP 404 error
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)

        with (
            patch.object(client._http_client, "get", side_effect=http_error),
            pytest.raises(ChannelNotFoundError),
        ):
            client.get_channel("nonexistent")

    def test_get_channel_other_error(
        self,
    ) -> None:
        """Test get_channel handles other errors."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock HTTP 500 error
        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = httpx.HTTPStatusError("Internal Server Error", request=MagicMock(), response=mock_response)

        with (
            patch.object(client._http_client, "get", side_effect=http_error),
            pytest.raises(ChannelNotFoundError),
        ):
            client.get_channel("channel_123")

    def test_get_channel_generic_exception(
        self,
    ) -> None:
        """Test get_channel handles generic exceptions."""
        from discord_client_impl.discord_impl import DiscordClient

        client = DiscordClient(access_token="test_token")

        # Mock generic exception
        network_error = RuntimeError("Network error")
        with (
            patch.object(client._http_client, "get", side_effect=network_error),
            pytest.raises(ChannelNotFoundError),
        ):
            client.get_channel("channel_123")


class TestDiscordClientThroughMainService:
    """Test DiscordClient methods through main_service integration."""

    def test_get_messages_through_main_service(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test get_messages is called through main_service."""
        from discord_client_impl.message_impl import DiscordMessage

        # Mock messages
        msg1_data = {
            "id": "msg_1",
            "channel_id": "channel_123",
            "content": "Message 1",
            "author": {"id": "user_1", "username": "user1"},
            "timestamp": "2024-01-01T00:00:00.000000+00:00",
            "edited_timestamp": None,
        }
        msg1 = DiscordMessage(msg1_data)

        msg2_data = {
            "id": "msg_2",
            "channel_id": "channel_123",
            "content": "Message 2",
            "author": {"id": "user_2", "username": "user2"},
            "timestamp": "2024-01-01T00:01:00.000000+00:00",
            "edited_timestamp": None,
        }
        msg2 = DiscordMessage(msg2_data)

        mock_discord_client.get_messages.return_value = [msg1, msg2]

        # Test through main_service
        seen = _initialize_seen_messages(mock_discord_client, "channel_123")

        assert "msg_1" in seen
        assert "msg_2" in seen
        mock_discord_client.get_messages.assert_called_once()

    def test_send_message_through_main_service(
        self,
        mock_discord_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test send_message is called through main_service."""
        from chat_client_impl.message_impl import ChatMessage
        from discord_client_impl.message_impl import DiscordMessage

        # Mock message
        msg_data = {
            "id": "msg_123",
            "channel_id": "channel_123",
            "content": "Create a ticket",
            "author": {"id": "user_123", "username": "testuser"},
            "timestamp": "2024-01-01T00:00:00.000000+00:00",
            "edited_timestamp": None,
        }
        discord_msg = DiscordMessage(msg_data)
        msg = ChatMessage(discord_msg)

        mock_discord_client.send_message.return_value = True

        # Mock AI to return no commands
        with patch("main_service.routing.ai_api.get_client") as mock_get_client:
            mock_ai_client = MagicMock()
            mock_ai_client.generate_response.return_value = "I understand your request."
            mock_get_client.return_value = mock_ai_client

            seen_message_ids: set[str] = set()
            _process_new_message(
                client=mock_discord_client,
                msg=msg,
                channel_id="channel_123",
                seen_message_ids=seen_message_ids,
                ticket_client=mock_tickets_client,
            )

            # Verify send_message was called
            assert mock_discord_client.send_message.called

    def test_delete_message_through_main_service(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test delete_message is called through main_service."""
        from discord_client_impl.message_impl import DiscordMessage

        # Mock test message
        test_msg_data = {
            "id": "test_msg",
            "channel_id": "channel_123",
            "content": "___BOT_ID_TEST___",
            "author": {"id": "bot_123", "username": "bot"},
            "timestamp": "2024-01-01T00:00:00.000000+00:00",
            "edited_timestamp": None,
        }
        test_msg = DiscordMessage(test_msg_data)

        mock_discord_client.send_message.return_value = True
        mock_discord_client.get_messages.return_value = [test_msg]
        mock_discord_client.delete_message.return_value = True

        # Test through _determine_bot_user_id
        bot_id = _determine_bot_user_id(mock_discord_client, "channel_123")

        assert bot_id == "bot_123"
        mock_discord_client.delete_message.assert_called_once()

    def test_filter_new_messages_excludes_bot(
        self,
    ) -> None:
        """Test _filter_new_messages excludes bot messages."""
        from chat_client_impl.message_impl import ChatMessage
        from discord_client_impl.message_impl import DiscordMessage

        user_msg_data = {
            "id": "msg_1",
            "channel_id": "channel_123",
            "content": "User message",
            "author": {"id": "user_123", "username": "user"},
            "timestamp": "2024-01-01T00:00:00.000000+00:00",
            "edited_timestamp": None,
        }
        user_discord_msg = DiscordMessage(user_msg_data)
        user_msg = ChatMessage(user_discord_msg)

        bot_msg_data = {
            "id": "msg_2",
            "channel_id": "channel_123",
            "content": "Bot message",
            "author": {"id": "bot_123", "username": "bot"},
            "timestamp": "2024-01-01T00:01:00.000000+00:00",
            "edited_timestamp": None,
        }
        bot_discord_msg = DiscordMessage(bot_msg_data)
        bot_msg = ChatMessage(bot_discord_msg)

        messages: list[chat_api.Message] = [user_msg, bot_msg]
        seen_ids: set[str] = set()
        bot_user_id = "bot_123"

        filtered = _filter_new_messages(messages, seen_ids, bot_user_id)

        assert len(filtered) == 1
        assert filtered[0].id == "msg_1"


@pytest.fixture
def mock_discord_client() -> MagicMock:
    """Mock Discord client for testing."""
    from discord_client_impl.discord_impl import DiscordClient

    mock_client = MagicMock(spec=DiscordClient)
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
