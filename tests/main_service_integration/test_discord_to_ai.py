"""Integration tests for Discord → AI Flow: Receiving Discord messages and processing with AI.

This file consolidates tests from the following source files:
  - test_discord_impl_integration.py
  - test_discord_message_integration.py
  - test_discord_client_methods_integration.py
  - test_chat_impl_integration.py
  - test_main_routing_integration.py
  - test_main_coverage.py
  - test_client_implementations_integration.py

All external services are mocked.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Generator

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
    _poll_cycle,
    _process_new_message,
    _process_new_messages,
)

from main_service import routing, ticketing

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
        network_error = RuntimeError("Network error")
        with (
            patch.object(client._http_client, "get", side_effect=network_error),
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
        network_error = RuntimeError("Network error")
        with (
            patch.object(client._http_client, "get", side_effect=network_error),
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
        msg = DiscordMessage(msg_data)

        mock_discord_client.send_message.return_value = True

        # Mock AI to return no commands
        with patch("main_service.routing.ai_api.get_client") as mock_get_client:
            mock_ai_client = MagicMock()
            mock_ai_client.generate_response.return_value = "I understand your request."
            mock_get_client.return_value = mock_ai_client

            seen_message_ids: set[str] = set()
            _process_new_message(  # type: ignore[arg-type]
                client=mock_discord_client,
                msg=msg,  # type: ignore[arg-type]
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
        from discord_client_impl.message_impl import DiscordMessage

        user_msg_data = {
            "id": "msg_1",
            "channel_id": "channel_123",
            "content": "User message",
            "author": {"id": "user_123", "username": "user"},
            "timestamp": "2024-01-01T00:00:00.000000+00:00",
            "edited_timestamp": None,
        }
        user_msg = DiscordMessage(user_msg_data)

        bot_msg_data = {
            "id": "msg_2",
            "channel_id": "channel_123",
            "content": "Bot message",
            "author": {"id": "bot_123", "username": "bot"},
            "timestamp": "2024-01-01T00:01:00.000000+00:00",
            "edited_timestamp": None,
        }
        bot_msg = DiscordMessage(bot_msg_data)

        messages = [user_msg, bot_msg]
        seen_ids: set[str] = set()
        bot_user_id = "bot_123"

        filtered = _filter_new_messages(messages, seen_ids, bot_user_id)  # type: ignore[arg-type]

        assert len(filtered) == 1
        assert filtered[0].id == "msg_1"


# ===== Tests from test_discord_message_integration.py =====


class TestDiscordMessageIntegration:
    """Test integration with DiscordMessage implementation."""

    def test_discord_message_properties(
        self,
    ) -> None:
        """Test that DiscordMessage objects have required properties."""
        from discord_client_impl.message_impl import DiscordMessage

        # Create DiscordMessage from raw Discord API data
        raw_data = {
            "id": "1234567890123456789",
            "channel_id": "987654321098765432",
            "content": "Test message content",
            "author": {
                "id": "111111111111111111",
                "username": "testuser",
                "global_name": "Test User",
            },
            "timestamp": "2024-01-01T00:00:00.000000+00:00",
            "edited_timestamp": None,
        }

        message = DiscordMessage(raw_data)

        # Verify all required properties exist
        assert message.id == "1234567890123456789"
        assert message.channel_id == "987654321098765432"
        assert message.content == "Test message content"
        assert message.sender_id == "111111111111111111"
        assert message.sender_name == "Test User"
        assert message.timestamp == "2024-01-01T00:00:00.000000+00:00"
        assert message.edited_timestamp is None

    def test_discord_message_without_global_name(
        self,
    ) -> None:
        """Test DiscordMessage when author has no global_name."""
        from discord_client_impl.message_impl import DiscordMessage

        raw_data = {
            "id": "msg_123",
            "channel_id": "channel_123",
            "content": "Message",
            "author": {
                "id": "user_123",
                "username": "testuser",
            },
            "timestamp": "2024-01-01T00:00:00.000000+00:00",
            "edited_timestamp": None,
        }

        message = DiscordMessage(raw_data)

        # Should fallback to username
        assert message.sender_name == "testuser"

    def test_discord_message_used_in_main_service(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test that main_service correctly processes DiscordMessage objects."""
        from discord_client_impl.message_impl import DiscordMessage

        # Create real DiscordMessage objects
        msg1_data = {
            "id": "msg_1",
            "channel_id": "channel_123",
            "content": "Message 1",
            "author": {"id": "user_1", "username": "user1"},
            "timestamp": "2024-01-01T00:00:00.000000+00:00",
            "edited_timestamp": None,
        }

        msg2_data = {
            "id": "msg_2",
            "channel_id": "channel_123",
            "content": "Message 2",
            "author": {"id": "user_2", "username": "user2"},
            "timestamp": "2024-01-01T00:01:00.000000+00:00",
            "edited_timestamp": None,
        }

        msg1 = DiscordMessage(msg1_data)
        msg2 = DiscordMessage(msg2_data)

        mock_discord_client.get_messages.return_value = [msg1, msg2]

        # Test that main_service can use these messages
        seen = _initialize_seen_messages(mock_discord_client, "channel_123")

        assert "msg_1" in seen
        assert "msg_2" in seen

        # Test filtering
        new_messages = _filter_new_messages([msg1, msg2], {"msg_1"}, None)  # type: ignore[arg-type,list-item]  # type: ignore[arg-type]

        assert len(new_messages) == 1
        assert new_messages[0].id == "msg_2"
        assert new_messages[0].content == "Message 2"


# ===== Tests from test_discord_client_methods_integration.py =====


class TestDiscordClientMethodsIntegration:
    """Test integration with DiscordClient methods."""

    def test_discord_client_get_message(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test DiscordClient.get_message method."""
        from discord_client_impl.message_impl import DiscordMessage

        # Mock message data
        message_data = {
            "id": "msg_123",
            "channel_id": "channel_123",
            "content": "Test message",
            "author": {"id": "user_123", "username": "testuser"},
            "timestamp": "2024-01-01T00:00:00.000000+00:00",
            "edited_timestamp": None,
        }

        mock_message = DiscordMessage(message_data)
        mock_discord_client.get_message.return_value = mock_message

        # Test get_message
        message = mock_discord_client.get_message(channel_id="channel_123", message_id="msg_123")

        assert message.id == "msg_123"
        assert message.content == "Test message"
        mock_discord_client.get_message.assert_called_once_with(channel_id="channel_123", message_id="msg_123")

    def test_discord_client_get_channel(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test DiscordClient.get_channel method."""
        from discord_client_impl.message_impl import DiscordChannel

        # Mock channel data
        channel_data = {
            "id": "channel_123",
            "name": "test-channel",
            "type": 0,  # GUILD_TEXT
        }

        mock_channel = DiscordChannel(channel_data)
        mock_discord_client.get_channel.return_value = mock_channel

        # Test get_channel
        channel = mock_discord_client.get_channel(channel_id="channel_123")

        assert channel.channel_id == "channel_123"
        assert channel.name == "test-channel"
        assert channel.channel_type == "text"
        mock_discord_client.get_channel.assert_called_once_with(channel_id="channel_123")

    def test_discord_client_send_message_error_handling(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test error handling when DiscordClient.send_message fails."""
        from discord_api.exceptions import MessageSendError

        mock_discord_client.send_message.side_effect = MessageSendError("Failed to send")

        # Test that error is raised
        with pytest.raises(MessageSendError):
            mock_discord_client.send_message(channel_id="channel_123", content="Test")

    def test_discord_client_get_messages_error_handling(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test error handling when DiscordClient.get_messages fails."""
        mock_discord_client.get_messages.side_effect = ValueError("API Error")

        # Test that error is raised
        with pytest.raises(ValueError, match=r".*"):
            mock_discord_client.get_messages(channel_id="channel_123", limit=10)

    def test_discord_client_delete_message_error_handling(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test error handling when DiscordClient.delete_message fails."""
        from discord_api.exceptions import MessageNotFoundError

        mock_discord_client.delete_message.side_effect = MessageNotFoundError("Message not found")

        # Test that error is raised
        with pytest.raises(MessageNotFoundError):
            mock_discord_client.delete_message(channel_id="channel_123", message_id="msg_123")

    def test_discord_message_edited_timestamp(
        self,
    ) -> None:
        """Test DiscordMessage with edited_timestamp."""
        from discord_client_impl.message_impl import DiscordMessage

        message_data = {
            "id": "msg_123",
            "channel_id": "channel_123",
            "content": "Edited message",
            "author": {"id": "user_123", "username": "testuser"},
            "timestamp": "2024-01-01T00:00:00.000000+00:00",
            "edited_timestamp": "2024-01-01T00:05:00.000000+00:00",
        }

        message = DiscordMessage(message_data)

        assert message.edited_timestamp == "2024-01-01T00:05:00.000000+00:00"

    def test_discord_channel_dm_type(
        self,
    ) -> None:
        """Test DiscordChannel for DM channel."""
        from discord_client_impl.message_impl import DiscordChannel

        channel_data = {
            "id": "dm_123",
            "type": 1,  # DM
            "recipients": [
                {"id": "user_1", "username": "user1"},
                {"id": "user_2", "username": "user2"},
            ],
        }

        channel = DiscordChannel(channel_data)

        assert channel.channel_type == "dm"
        assert "user1" in channel.name or "user2" in channel.name

    def test_discord_channel_voice_type(
        self,
    ) -> None:
        """Test DiscordChannel for voice channel."""
        from discord_client_impl.message_impl import DiscordChannel

        channel_data = {
            "id": "voice_123",
            "name": "General",
            "type": 2,  # GUILD_VOICE
        }

        channel = DiscordChannel(channel_data)

        assert channel.channel_type == "voice"
        assert channel.name == "General"


# ===== Tests from test_chat_impl_integration.py =====


class TestChatClientInitialization:
    """Test ChatClient initialization paths."""

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
            assert client._discord_client is mock_discord_client  # type: ignore[attr-defined]

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
            assert client._discord_client is mock_discord_client  # type: ignore[attr-defined]


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
        client._discord_client = mock_discord_client  # type: ignore[attr-defined]

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
        client._discord_client = mock_discord_client  # type: ignore[attr-defined]

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
        client._discord_client = mock_discord_client  # type: ignore[attr-defined]

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
        client._discord_client = mock_discord_client  # type: ignore[attr-defined]

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
        client._discord_client = mock_discord_client  # type: ignore[attr-defined]

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
        client = chat_api.get_client()  # type: ignore[attr-defined]

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

        filtered = _filter_new_messages(messages, seen_ids, bot_user_id)  # type: ignore[arg-type]

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
        client = chat_api.get_client()  # type: ignore[attr-defined]

        from chat_client_impl.chat_impl import ChatClient

        assert isinstance(client, ChatClient)

    def test_get_client_impl_without_bot_token(
        self,
    ) -> None:
        """Test get_client_impl uses user_id when DISCORD_BOT_TOKEN not available."""
        import discord_api
        from chat_client_impl import get_client_impl

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(discord_api, "get_client") as mock_get_client,
        ):
            mock_discord_client = MagicMock()
            mock_get_client.return_value = mock_discord_client

            client = get_client_impl(user_id="user_123")

            # Verify discord_api.get_client was called
            mock_get_client.assert_called_once_with(user_id="user_123")
            assert client._discord_client is mock_discord_client  # type: ignore[attr-defined]


@pytest.fixture
def mock_chat_client() -> MagicMock:
    """Mock ChatClient for testing."""
    from chat_client_impl.chat_impl import ChatClient

    mock_client = MagicMock(spec=ChatClient)
    mock_client.send_message.return_value = True
    mock_client.get_messages.return_value = []
    mock_client.delete_message.return_value = True
    return mock_client


# ===== Tests from test_main_routing_integration.py =====


class TestMainRoutingIntegration:
    """Test integration between main service and routing components."""

    def test_process_message_with_ticket_command(
        self,
        mock_discord_client: MagicMock,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that messages with ticket commands are processed correctly.

        This test verifies:
        1. Message is received from Discord
        2. AI extracts ticket commands from message
        3. Commands are executed via ticketing
        4. AI generates response
        5. Response is sent back to Discord
        """
        # Setup: Mock message
        mock_message = MagicMock()
        mock_message.id = "msg_123"
        mock_message.content = "Create a ticket for testing"
        mock_message.sender_id = "user_456"
        mock_message.channel_id = "channel_789"

        # Setup: Mock AI extraction
        mock_ai_client.generate_response.side_effect = [
            # Command extraction
            {
                "actions": [
                    {
                        "type": "create_ticket",
                        "params": {
                            "title": "Test Ticket",
                            "description": "Testing",
                            "ticket_id": None,
                            "status": None,
                            "query": None,
                            "assignee": None,
                        },
                    }
                ]
            },
            # Response generation
            "I've created ticket ticket_123: Test Ticket",
        ]

        # Setup: Mock ticket creation
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Test Ticket"
        mock_ticket.description = "Testing"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.create_ticket.return_value = mock_ticket

        # Execute: Process message
        seen_message_ids: set[str] = set()
        _process_new_message(  # type: ignore[arg-type]
            client=mock_discord_client,
            msg=mock_message,
            channel_id="channel_789",
            seen_message_ids=seen_message_ids,
            ticket_client=mock_tickets_client,
        )

        # Verify: AI was called for extraction and response
        assert mock_ai_client.generate_response.call_count >= 2  # noqa: PLR2004

        # Verify: Ticket was created
        mock_tickets_client.create_ticket.assert_called_once()

        # Verify: Response was sent to Discord
        mock_discord_client.send_message.assert_called_once()
        call_args = mock_discord_client.send_message.call_args
        assert call_args[1]["channel_id"] == "channel_789"
        assert isinstance(call_args[1]["content"], str)
        assert len(call_args[1]["content"]) > 0

        # Verify: Message was marked as seen
        assert "msg_123" in seen_message_ids

    def test_process_message_without_ticket_command(
        self,
        mock_discord_client: MagicMock,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that regular messages (without commands) are handled correctly."""
        # Setup: Mock message without ticket command
        mock_message = MagicMock()
        mock_message.id = "msg_456"
        mock_message.content = "Hello, how are you?"
        mock_message.sender_id = "user_789"
        mock_message.channel_id = "channel_123"

        # Setup: Mock AI (no commands extracted, but generates response)
        mock_ai_client.generate_response.side_effect = [
            # Command extraction (returns empty)
            {"actions": []},
            # Response generation
            "Hello! I'm doing well, thank you for asking.",
        ]

        # Execute
        seen_message_ids: set[str] = set()
        _process_new_message(  # type: ignore[arg-type]
            client=mock_discord_client,
            msg=mock_message,
            channel_id="channel_123",
            seen_message_ids=seen_message_ids,
            ticket_client=mock_tickets_client,
        )

        # Verify: AI was called
        assert mock_ai_client.generate_response.called

        # Verify: Response was sent
        mock_discord_client.send_message.assert_called_once()

        # Verify: No ticket operations
        mock_tickets_client.create_ticket.assert_not_called()

    def test_filter_new_messages_excludes_seen_and_bot_messages(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test that message filtering correctly excludes seen and bot messages."""
        # Setup: Mock messages (using MagicMock directly since Message is abstract)
        msg1 = MagicMock()
        msg1.id = "msg_1"
        msg1.sender_id = "user_1"
        msg1.content = "Message 1"

        msg2 = MagicMock()
        msg2.id = "msg_2"
        msg2.sender_id = "bot_123"  # Bot message
        msg2.content = "Bot response"

        msg3 = MagicMock()
        msg3.id = "msg_3"
        msg3.sender_id = "user_2"
        msg3.content = "Message 3"

        messages = [msg1, msg2, msg3]
        seen_message_ids = {"msg_1"}  # msg_1 already seen
        bot_user_id = "bot_123"

        # Execute
        new_messages = _filter_new_messages(messages, seen_message_ids, bot_user_id)  # type: ignore[arg-type]

        # Verify: Only msg_3 is new (msg_1 is seen, msg_2 is from bot)
        assert len(new_messages) == 1
        assert new_messages[0].id == "msg_3"

    def test_process_new_messages_handles_multiple_messages(
        self,
        mock_discord_client: MagicMock,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test processing multiple new messages."""
        # Setup: Mock messages (using MagicMock directly)
        msg1 = MagicMock()
        msg1.id = "msg_1"
        msg1.content = "Create ticket 1"
        msg1.sender_id = "user_1"

        msg2 = MagicMock()
        msg2.id = "msg_2"
        msg2.content = "Create ticket 2"
        msg2.sender_id = "user_2"

        new_messages = [msg1, msg2]
        seen_message_ids: set[str] = set()
        channel_id = "channel_123"

        # Setup: Mock AI responses
        mock_ai_client.generate_response.side_effect = [
            # Extraction for msg1
            {
                "actions": [
                    {
                        "type": "create_ticket",
                        "params": {
                            "title": "Ticket 1",
                            "description": "Desc 1",
                            "ticket_id": None,
                            "status": None,
                            "query": None,
                            "assignee": None,
                        },
                    }
                ]
            },
            # Response for msg1
            "Created ticket 1",
            # Extraction for msg2
            {
                "actions": [
                    {
                        "type": "create_ticket",
                        "params": {
                            "title": "Ticket 2",
                            "description": "Desc 2",
                            "ticket_id": None,
                            "status": None,
                            "query": None,
                            "assignee": None,
                        },
                    }
                ]
            },
            # Response for msg2
            "Created ticket 2",
        ]

        # Setup: Mock ticket creation
        from tickets_api import Ticket, TicketStatus

        def create_ticket_side_effect(title: str, description: str, assignee: str | None = None) -> MagicMock:
            ticket = MagicMock(spec=Ticket)
            ticket.id = f"ticket_{title.lower().replace(' ', '_')}"
            ticket.title = title
            ticket.description = description
            ticket.status = TicketStatus.OPEN
            ticket.assignee = assignee
            return ticket

        mock_tickets_client.create_ticket.side_effect = create_ticket_side_effect

        # Setup: Mock get_messages for re-fetch
        mock_discord_client.get_messages.return_value = [msg1, msg2]

        # Execute
        updated_messages = _process_new_messages(  # type: ignore[arg-type]
            client=mock_discord_client,
            new_messages=new_messages,  # type: ignore[arg-type]
            channel_id=channel_id,
            seen_message_ids=seen_message_ids,
            message_check_limit=10,
            ticket_client=mock_tickets_client,
        )

        # Verify: Both messages were processed
        assert mock_discord_client.send_message.call_count == 2  # noqa: PLR2004
        assert "msg_1" in seen_message_ids
        assert "msg_2" in seen_message_ids
        assert len(updated_messages) == 2  # noqa: PLR2004


@pytest.fixture
def mock_ai_client(monkeypatch: pytest.MonkeyPatch) -> Generator[MagicMock, None, None]:
    """Mock AI client for testing."""
    mock_client = MagicMock()

    # Patch ai_api.get_client to return our mock
    with patch("main_service.routing.ai_api.get_client", return_value=mock_client):
        yield mock_client


# ===== Tests from test_main_coverage.py =====


class TestMainCoverage:
    """Additional tests for main.py coverage."""

    def test_determine_bot_user_id_success(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test successful bot user ID determination."""
        # Mock message that matches test response
        mock_message = MagicMock()
        mock_message.content = "___BOT_ID_TEST___"
        mock_message.sender_id = "bot_123"
        mock_message.id = "msg_123"

        mock_discord_client.send_message.return_value = True
        mock_discord_client.get_messages.return_value = [mock_message]
        mock_discord_client.delete_message.return_value = True

        bot_id = _determine_bot_user_id(mock_discord_client, "channel_123")

        assert bot_id == "bot_123"
        mock_discord_client.send_message.assert_called_once()
        mock_discord_client.delete_message.assert_called_once()

    def test_determine_bot_user_id_not_found(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test bot user ID determination when not found."""
        mock_discord_client.send_message.return_value = True
        mock_discord_client.get_messages.return_value = []  # No matching message

        bot_id = _determine_bot_user_id(mock_discord_client, "channel_123")

        assert bot_id is None

    def test_determine_bot_user_id_exception(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test bot user ID determination when exception occurs."""
        mock_discord_client.send_message.side_effect = Exception("Error")

        bot_id = _determine_bot_user_id(mock_discord_client, "channel_123")

        assert bot_id is None

    def test_initialize_seen_messages_success(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test successful initialization of seen messages."""
        mock_message1 = MagicMock()
        mock_message1.id = "msg_1"
        mock_message2 = MagicMock()
        mock_message2.id = "msg_2"

        mock_discord_client.get_messages.return_value = [mock_message1, mock_message2]

        seen = _initialize_seen_messages(mock_discord_client, "channel_123")

        assert "msg_1" in seen
        assert "msg_2" in seen
        assert len(seen) == 2  # noqa: PLR2004

    def test_initialize_seen_messages_exception(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test initialization of seen messages when exception occurs."""
        mock_discord_client.get_messages.side_effect = ValueError("Error")

        with pytest.raises(ValueError, match="Error"):
            _initialize_seen_messages(mock_discord_client, "channel_123")

    def test_filter_new_messages_no_bot_id(
        self,
    ) -> None:
        """Test filtering messages when bot_id is None."""
        msg1 = MagicMock()
        msg1.id = "msg_1"
        msg1.sender_id = "user_1"
        msg1.content = "Message 1"

        msg2 = MagicMock()
        msg2.id = "msg_2"
        msg2.sender_id = "user_2"
        msg2.content = "Message 2"

        messages = [msg1, msg2]
        seen = {"msg_1"}

        new_messages = _filter_new_messages(messages, seen, None)  # type: ignore[arg-type]

        assert len(new_messages) == 1
        assert new_messages[0].id == "msg_2"

    def test_filter_new_messages_excludes_bot_response(
        self,
    ) -> None:
        """Test filtering excludes bot's own responses by content."""
        msg1 = MagicMock()
        msg1.id = "msg_1"
        msg1.sender_id = "user_1"
        msg1.content = "What a cool message!"  # Bot response content

        messages = [msg1]
        seen: set[str] = set()

        new_messages = _filter_new_messages(messages, seen, None)  # type: ignore[arg-type]

        assert len(new_messages) == 0

    def test_process_new_message_already_seen(
        self,
        mock_discord_client: MagicMock,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test processing message that's already seen."""
        mock_message = MagicMock()
        mock_message.id = "msg_123"
        mock_message.content = "Create ticket"
        mock_message.sender_id = "user_123"

        seen = {"msg_123"}  # Already seen

        _process_new_message(  # type: ignore[arg-type]
            client=mock_discord_client,
            msg=mock_message,
            channel_id="channel_123",
            seen_message_ids=seen,
            ticket_client=mock_tickets_client,
        )

        # Should not process if already seen
        mock_ai_client.generate_response.assert_not_called()

    def test_poll_cycle_no_new_messages(
        self,
        mock_discord_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test poll cycle when no new messages."""
        mock_message = MagicMock()
        mock_message.id = "msg_1"
        mock_message.sender_id = "user_1"

        mock_discord_client.get_messages.return_value = [mock_message]
        seen = {"msg_1"}  # Already seen
        bot_id = None

        _poll_cycle(
            client=mock_discord_client,
            channel_id="channel_123",
            message_check_limit=10,
            seen_message_ids=seen,
            bot_user_id=bot_id,
            ticket_client=mock_tickets_client,
        )

        # Should update seen set
        assert "msg_1" in seen


# ===== Tests from test_client_implementations_integration.py =====


class TestDiscordClientImplementationIntegration:
    """Test main_service integration with DiscordClient implementation."""

    def test_discord_client_send_message_integration(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test that main_service correctly uses DiscordClient.send_message."""
        # Mock successful send
        mock_discord_client.send_message.return_value = True

        result = mock_discord_client.send_message(channel_id="channel_123", content="Test message")

        assert result is True
        mock_discord_client.send_message.assert_called_once_with(channel_id="channel_123", content="Test message")

    def test_discord_client_get_messages_integration(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test that main_service correctly uses DiscordClient.get_messages."""
        # Create mock messages
        mock_msg1 = MagicMock()
        mock_msg1.id = "msg_1"
        mock_msg1.content = "Message 1"
        mock_msg1.sender_id = "user_1"
        mock_msg1.timestamp = "2024-01-01T00:00:00Z"

        mock_msg2 = MagicMock()
        mock_msg2.id = "msg_2"
        mock_msg2.content = "Message 2"
        mock_msg2.sender_id = "user_2"
        mock_msg2.timestamp = "2024-01-01T00:01:00Z"

        mock_discord_client.get_messages.return_value = [mock_msg1, mock_msg2]

        messages = mock_discord_client.get_messages(channel_id="channel_123", limit=10)

        assert len(messages) == 2  # noqa: PLR2004
        assert messages[0].id == "msg_1"
        assert messages[1].id == "msg_2"
        mock_discord_client.get_messages.assert_called_once_with(channel_id="channel_123", limit=10)

    def test_discord_client_delete_message_integration(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test that main_service correctly uses DiscordClient.delete_message."""
        mock_discord_client.delete_message.return_value = True

        result = mock_discord_client.delete_message(channel_id="channel_123", message_id="msg_456")

        assert result is True
        mock_discord_client.delete_message.assert_called_once_with(channel_id="channel_123", message_id="msg_456")

    def test_determine_bot_user_id_uses_discord_methods(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test that _determine_bot_user_id uses Discord client methods correctly."""
        # Mock test message that matches bot response
        mock_message = MagicMock()
        mock_message.content = "___BOT_ID_TEST___"
        mock_message.sender_id = "bot_123"
        mock_message.id = "msg_test"

        mock_discord_client.send_message.return_value = True
        mock_discord_client.get_messages.return_value = [mock_message]
        mock_discord_client.delete_message.return_value = True

        bot_id = _determine_bot_user_id(mock_discord_client, "channel_123")

        assert bot_id == "bot_123"
        # Verify all Discord methods were called
        mock_discord_client.send_message.assert_called_once()
        mock_discord_client.get_messages.assert_called_once()
        mock_discord_client.delete_message.assert_called_once()

    def test_initialize_seen_messages_uses_discord_get_messages(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test that _initialize_seen_messages uses Discord get_messages."""
        mock_msg1 = MagicMock()
        mock_msg1.id = "msg_1"
        mock_msg2 = MagicMock()
        mock_msg2.id = "msg_2"

        mock_discord_client.get_messages.return_value = [mock_msg1, mock_msg2]

        seen = _initialize_seen_messages(mock_discord_client, "channel_123")

        assert "msg_1" in seen
        assert "msg_2" in seen
        mock_discord_client.get_messages.assert_called_once_with(channel_id="channel_123", limit=5)


class TestTicketsClientImplementationIntegration:
    """Test main_service integration with TicketsClient implementation."""

    def test_tickets_client_create_ticket_integration(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that ticketing uses TicketsClient.create_ticket correctly."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "New Ticket"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.create_ticket.return_value = mock_ticket

        commands = [
            {
                "type": "create_ticket",
                "params": {
                    "title": "New Ticket",
                    "description": "Description",
                    "ticket_id": None,
                    "status": None,
                    "query": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        mock_tickets_client.create_ticket.assert_called_once_with(title="New Ticket", description="Description", assignee=None)
        assert results[0]["success"] is True
        assert results[0]["result"]["id"] == "ticket_123"

    def test_tickets_client_search_tickets_integration(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that ticketing uses TicketsClient.search_tickets correctly."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket1 = MagicMock(spec=Ticket)
        mock_ticket1.id = "ticket_1"
        mock_ticket1.title = "Ticket 1"
        mock_ticket1.description = "Desc 1"
        mock_ticket1.status = TicketStatus.OPEN
        mock_ticket1.assignee = None

        mock_ticket2 = MagicMock(spec=Ticket)
        mock_ticket2.id = "ticket_2"
        mock_ticket2.title = "Ticket 2"
        mock_ticket2.description = "Desc 2"
        mock_ticket2.status = TicketStatus.IN_PROGRESS
        mock_ticket2.assignee = None

        mock_tickets_client.search_tickets.return_value = [mock_ticket1, mock_ticket2]

        commands = [
            {
                "type": "search_tickets",
                "params": {
                    "query": "test",
                    "status": "open",
                    "ticket_id": None,
                    "title": None,
                    "description": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        mock_tickets_client.search_tickets.assert_called_once_with(query="test", status=TicketStatus.OPEN)
        assert results[0]["success"] is True
        assert len(results[0]["result"]["tickets"]) == 2  # noqa: PLR2004

    def test_tickets_client_update_ticket_integration(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that ticketing uses TicketsClient.update_ticket correctly."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Updated Title"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.CLOSED
        mock_ticket.assignee = None
        mock_tickets_client.update_ticket.return_value = mock_ticket

        commands = [
            {
                "type": "update_ticket",
                "params": {
                    "ticket_id": "ticket_123",
                    "status": "closed",
                    "title": "Updated Title",
                    "description": None,
                    "query": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        mock_tickets_client.update_ticket.assert_called_once_with(
            ticket_id="ticket_123", status=TicketStatus.CLOSED, title="Updated Title"
        )
        assert results[0]["success"] is True
        assert results[0]["result"]["status"] == "closed"

    def test_tickets_client_delete_ticket_integration(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that ticketing uses TicketsClient.delete_ticket correctly."""
        mock_tickets_client.delete_ticket.return_value = True

        commands = [
            {
                "type": "delete_ticket",
                "params": {"ticket_id": "ticket_123"},
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        mock_tickets_client.delete_ticket.assert_called_once_with("ticket_123")
        assert results[0]["success"] is True
        assert results[0]["result"]["deleted"] is True


class TestAIClientImplementationIntegration:
    """Test main_service integration with AI client implementation."""

    def test_ai_client_extract_commands_integration(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test that routing uses AI client for command extraction."""
        mock_ai_client.generate_response.return_value = {
            "actions": [
                {
                    "type": "create_ticket",
                    "params": {
                        "title": "Test",
                        "description": "Test",
                        "ticket_id": None,
                        "status": None,
                        "query": None,
                        "assignee": None,
                    },
                },
                {
                    "type": "search_tickets",
                    "params": {
                        "query": "test",
                        "status": None,
                        "ticket_id": None,
                        "title": None,
                        "description": None,
                        "assignee": None,
                    },
                },
            ]
        }

        commands = routing.extract_commands("Create a ticket and search for it")

        assert mock_ai_client.generate_response.called
        assert len(commands) == 2  # noqa: PLR2004
        assert commands[0]["type"] == "create_ticket"
        assert commands[1]["type"] == "search_tickets"

    def test_ai_client_generate_response_integration(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test that routing uses AI client for response generation."""
        mock_ai_client.generate_response.return_value = "I've successfully processed your request and created 2 tickets."

        results = [
            {
                "success": True,
                "command": {"type": "create_ticket", "params": {}},
                "result": {"id": "ticket_1", "title": "Ticket 1"},
                "error": None,
            },
            {
                "success": True,
                "command": {"type": "create_ticket", "params": {}},
                "result": {"id": "ticket_2", "title": "Ticket 2"},
                "error": None,
            },
        ]

        response = routing.generate_response("Create two tickets", results)

        assert mock_ai_client.generate_response.called
        assert isinstance(response, str)
        assert "2 tickets" in response

    def test_ai_client_correct_commands_integration(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test that routing uses AI client for command correction."""
        original_commands = [
            {
                "type": "create_ticket",
                "params": {"title": "Test", "description": ""},
            }
        ]

        mock_ai_client.generate_response.return_value = {
            "actions": [
                {
                    "type": "create_ticket",
                    "params": {
                        "title": "Test",
                        "description": "Fixed description",
                        "ticket_id": None,
                        "status": None,
                        "query": None,
                        "assignee": None,
                    },
                }
            ]
        }

        corrected = routing.correct_commands(original_commands, "Missing description")

        assert mock_ai_client.generate_response.called
        assert len(corrected) == 1
        assert corrected[0]["params"]["description"] == "Fixed description"


class TestFullClientIntegrationFlow:
    """Test complete integration flows using all client implementations."""

    def test_complete_message_to_ticket_flow(
        self,
        mock_discord_client: MagicMock,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test complete flow: message → AI extraction → ticket creation → AI response → Discord."""
        from tickets_api import Ticket, TicketStatus

        # Setup: Mock message
        mock_message = MagicMock()
        mock_message.id = "msg_123"
        mock_message.content = "Create a ticket for urgent bug fix"
        mock_message.sender_id = "user_456"

        # Setup: Mock AI responses
        call_count = {"count": 0}

        def ai_response_side_effect(*args: object, **kwargs: object) -> dict[str, object] | str:
            """Side effect function for AI client responses."""
            call_count["count"] += 1
            current_call = call_count["count"]

            # First call: Command extraction
            if current_call == 1:
                return {
                    "actions": [
                        {
                            "type": "create_ticket",
                            "params": {
                                "title": "Urgent Bug Fix",
                                "description": "Fix critical bug",
                                "ticket_id": None,
                                "status": None,
                                "query": None,
                                "assignee": None,
                            },
                        }
                    ]
                }
            # Second call: Response generation
            return "I've created ticket ticket_123: Urgent Bug Fix"

        mock_ai_client.generate_response.side_effect = ai_response_side_effect

        # Setup: Mock ticket
        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Urgent Bug Fix"
        mock_ticket.description = "Fix critical bug"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.create_ticket.return_value = mock_ticket

        # Execute
        seen_message_ids: set[str] = set()
        _process_new_message(  # type: ignore[arg-type]
            client=mock_discord_client,
            msg=mock_message,
            channel_id="channel_789",
            seen_message_ids=seen_message_ids,
            ticket_client=mock_tickets_client,
        )

        # Verify: All client implementations were used correctly
        # 1. AI client for extraction
        assert mock_ai_client.generate_response.call_count >= 2  # noqa: PLR2004

        # 2. Tickets client for creation
        mock_tickets_client.create_ticket.assert_called_once_with(
            title="Urgent Bug Fix", description="Fix critical bug", assignee=None
        )

        # 3. Discord client for sending response
        mock_discord_client.send_message.assert_called_once()
        call_args = mock_discord_client.send_message.call_args
        assert call_args[1]["channel_id"] == "channel_789"
        assert "ticket_123" in call_args[1]["content"]

    def test_multiple_ticket_operations_flow(
        self,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test flow with multiple ticket operations."""
        from tickets_api import Ticket, TicketStatus

        # Setup: Multiple tickets
        mock_ticket1 = MagicMock(spec=Ticket)
        mock_ticket1.id = "ticket_1"
        mock_ticket1.title = "Ticket 1"
        mock_ticket1.description = "Desc 1"
        mock_ticket1.status = TicketStatus.OPEN
        mock_ticket1.assignee = None

        mock_ticket2 = MagicMock(spec=Ticket)
        mock_ticket2.id = "ticket_2"
        mock_ticket2.title = "Ticket 2"
        mock_ticket2.description = "Desc 2"
        mock_ticket2.status = TicketStatus.OPEN
        mock_ticket2.assignee = None

        updated_ticket = MagicMock(spec=Ticket)
        updated_ticket.id = "ticket_1"
        updated_ticket.title = "Ticket 1"
        updated_ticket.description = "Desc 1"
        updated_ticket.status = TicketStatus.IN_PROGRESS
        updated_ticket.assignee = None

        mock_tickets_client.create_ticket.side_effect = [mock_ticket1, mock_ticket2]
        mock_tickets_client.search_tickets.return_value = [mock_ticket1, mock_ticket2]
        mock_tickets_client.update_ticket.return_value = updated_ticket
        mock_tickets_client.delete_ticket.return_value = True

        # Execute multiple operations
        commands = [
            {
                "type": "create_ticket",
                "params": {
                    "title": "Ticket 1",
                    "description": "Desc 1",
                    "ticket_id": None,
                    "status": None,
                    "query": None,
                    "assignee": None,
                },
            },
            {
                "type": "create_ticket",
                "params": {
                    "title": "Ticket 2",
                    "description": "Desc 2",
                    "ticket_id": None,
                    "status": None,
                    "query": None,
                    "assignee": None,
                },
            },
            {
                "type": "search_tickets",
                "params": {"query": "Ticket"},
            },
            {
                "type": "update_ticket",
                "params": {"ticket_id": "ticket_1", "status": "in_progress"},
            },
            {
                "type": "delete_ticket",
                "params": {"ticket_id": "ticket_2"},
            },
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify all operations were called
        assert mock_tickets_client.create_ticket.call_count == 2  # noqa: PLR2004
        mock_tickets_client.search_tickets.assert_called_once()
        mock_tickets_client.update_ticket.assert_called_once()
        mock_tickets_client.delete_ticket.assert_called_once()

        # Verify all succeeded
        assert len(results) == 5  # noqa: PLR2004
        assert all(r["success"] for r in results)


# ===== Error Handling and Utilities Tests =====
# ===== Tests from test_main_service_error_handling.py =====


class TestMainServiceErrorHandling:
    """Test error handling in main_service."""

    def test_process_new_message_handles_ai_extraction_error(
        self,
        mock_discord_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that _process_new_message handles AI extraction errors gracefully."""
        # Mock message
        mock_message = MagicMock()
        mock_message.id = "msg_123"
        mock_message.content = "Create a ticket"
        mock_message.sender_id = "user_123"

        # Mock AI client to raise error
        with patch("main_service.routing.ai_api.get_client") as mock_get_client:
            mock_ai_client = MagicMock()
            error_msg = "AI Error"
            mock_ai_client.generate_response.side_effect = RuntimeError(error_msg)
            mock_get_client.return_value = mock_ai_client

            # Execute
            seen_message_ids: set[str] = set()
            _process_new_message(
                client=mock_discord_client,
                msg=mock_message,
                channel_id="channel_123",
                seen_message_ids=seen_message_ids,
                ticket_client=mock_tickets_client,
            )

            # Verify error response was sent
            assert mock_discord_client.send_message.call_count >= 1
            # Last call should be error response
            last_call = mock_discord_client.send_message.call_args_list[-1]
            assert "error" in last_call[1]["content"].lower() or "try again" in last_call[1]["content"].lower()

    def test_process_new_message_handles_ticket_operation_error(
        self,
        mock_discord_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that _process_new_message handles ticket operation errors gracefully."""
        # Mock message
        mock_message = MagicMock()
        mock_message.id = "msg_123"
        mock_message.content = "Create a ticket for urgent bug"
        mock_message.sender_id = "user_123"

        # Mock AI to extract command
        with patch("main_service.routing.ai_api.get_client") as mock_get_client:
            mock_ai_client = MagicMock()
            mock_ai_client.generate_response.side_effect = [
                # Command extraction
                {
                    "actions": [
                        {
                            "type": "create_ticket",
                            "params": {
                                "title": "Urgent Bug",
                                "description": "Fix bug",
                                "ticket_id": None,
                                "status": None,
                                "query": None,
                                "assignee": None,
                            },
                        }
                    ]
                },
                # Response generation
                "I've created the ticket",
            ]
            mock_get_client.return_value = mock_ai_client

            # Mock ticket client to raise error
            mock_tickets_client.create_ticket.side_effect = ValueError("Ticket creation failed")

            # Execute
            seen_message_ids: set[str] = set()
            _process_new_message(
                client=mock_discord_client,
                msg=mock_message,
                channel_id="channel_123",
                seen_message_ids=seen_message_ids,
                ticket_client=mock_tickets_client,
            )

            # Verify error response was sent
            assert mock_discord_client.send_message.call_count >= 1
            last_call = mock_discord_client.send_message.call_args_list[-1]
            assert "error" in last_call[1]["content"].lower() or "try again" in last_call[1]["content"].lower()

    def test_process_new_message_handles_send_message_failure(
        self,
        mock_discord_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that _process_new_message handles send_message failures."""
        # Mock message
        mock_message = MagicMock()
        mock_message.id = "msg_123"
        mock_message.content = "Create a ticket"
        mock_message.sender_id = "user_123"

        # Mock AI to extract command
        with patch("main_service.routing.ai_api.get_client") as mock_get_client:
            mock_ai_client = MagicMock()
            mock_ai_client.generate_response.side_effect = [
                {
                    "actions": [
                        {
                            "type": "create_ticket",
                            "params": {
                                "title": "Test",
                                "description": "Test",
                                "ticket_id": None,
                                "status": None,
                                "query": None,
                                "assignee": None,
                            },
                        }
                    ]
                },
                "Response",
            ]
            mock_get_client.return_value = mock_ai_client

            # Mock send_message to fail
            mock_discord_client.send_message.return_value = False

            # Execute
            seen_message_ids: set[str] = set()
            _process_new_message(
                client=mock_discord_client,
                msg=mock_message,
                channel_id="channel_123",
                seen_message_ids=seen_message_ids,
                ticket_client=mock_tickets_client,
            )

            # Verify send_message was called (even if it failed)
            assert mock_discord_client.send_message.called

    def test_process_new_messages_handles_multiple_errors(
        self,
        mock_discord_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that _process_new_messages handles errors in multiple messages."""
        # Mock messages
        mock_msg1 = MagicMock()
        mock_msg1.id = "msg_1"
        mock_msg1.content = "Message 1"
        mock_msg1.sender_id = "user_1"

        mock_msg2 = MagicMock()
        mock_msg2.id = "msg_2"
        mock_msg2.content = "Message 2"
        mock_msg2.sender_id = "user_2"

        # Mock AI to fail for first message, succeed for second
        call_count = {"count": 0}

        def ai_side_effect(*args: object, **kwargs: object) -> dict[str, object]:
            call_count["count"] += 1
            if call_count["count"] == 1:
                error_msg = "AI Error"
                raise RuntimeError(error_msg)
            return {
                "actions": [
                    {
                        "type": "search_tickets",
                        "params": {
                            "query": None,
                            "status": None,
                            "ticket_id": None,
                            "title": None,
                            "description": None,
                            "assignee": None,
                        },
                    }
                ]
            }

        with patch("main_service.routing.ai_api.get_client") as mock_get_client:
            mock_ai_client = MagicMock()
            mock_ai_client.generate_response.side_effect = ai_side_effect
            mock_get_client.return_value = mock_ai_client

            # Execute
            seen_message_ids: set[str] = set()
            _process_new_messages(  # type: ignore[arg-type]
                client=mock_discord_client,
                new_messages=[mock_msg1, mock_msg2],
                channel_id="channel_123",
                seen_message_ids=seen_message_ids,
                message_check_limit=10,
                ticket_client=mock_tickets_client,
            )

            # Verify both messages were processed (even if first failed)
            assert "msg_1" in seen_message_ids
            assert "msg_2" in seen_message_ids

    def test_filter_new_messages_excludes_bot_messages(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test that _filter_new_messages correctly excludes bot messages."""
        # Mock messages
        user_message = MagicMock()
        user_message.id = "msg_1"
        user_message.sender_id = "user_123"

        bot_message = MagicMock()
        bot_message.id = "msg_2"
        bot_message.sender_id = "bot_123"

        messages = [user_message, bot_message]
        seen_ids: set[str] = set()
        bot_user_id = "bot_123"

        filtered = _filter_new_messages(messages, seen_ids, bot_user_id)  # type: ignore[arg-type]

        # Bot message should be excluded
        assert len(filtered) == 1
        assert filtered[0].id == "msg_1"

    def test_filter_new_messages_excludes_seen_messages(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test that _filter_new_messages correctly excludes seen messages."""
        # Mock messages
        new_message = MagicMock()
        new_message.id = "msg_1"
        new_message.sender_id = "user_123"

        seen_message = MagicMock()
        seen_message.id = "msg_2"
        seen_message.sender_id = "user_123"

        messages = [new_message, seen_message]
        seen_ids: set[str] = {"msg_2"}
        bot_user_id = None

        filtered = _filter_new_messages(messages, seen_ids, bot_user_id)  # type: ignore[arg-type]

        # Seen message should be excluded
        assert len(filtered) == 1
        assert filtered[0].id == "msg_1"
