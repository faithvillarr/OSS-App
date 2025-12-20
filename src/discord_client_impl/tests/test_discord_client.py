"""Unit tests for DiscordClient HTTP methods with mocked responses."""

from unittest.mock import MagicMock, patch

import pytest
import respx
from discord_api.exceptions import (
    AuthenticationError,
    ChannelNotFoundError,
    MessageDeleteError,
    MessageNotFoundError,
    MessageSendError,
)
from httpx import Response
from respx import MockRouter

from discord_client_impl.discord_impl import DiscordClient

# Test constants
MIN_STATE_LENGTH = 10  # Minimum length for OAuth2 state parameter
DISCORD_TOKEN_EXPIRES_IN = 604800  # Discord token expiration time in seconds (7 days)
EXPECTED_MESSAGE_COUNT = 2  # Expected number of messages in test responses
EXPECTED_CHANNEL_COUNT = 2  # Expected number of channels in test responses


@pytest.fixture
def discord_client() -> DiscordClient:
    """Create a DiscordClient with test credentials."""
    return DiscordClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        redirect_uri="http://localhost:8000/callback",
        access_token="test_access_token",
    )


@pytest.fixture
def auth_client() -> DiscordClient:
    """Create a DiscordClient without access token for OAuth tests."""
    return DiscordClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        redirect_uri="http://localhost:8000/callback",
    )


class TestOAuth2Flow:
    """Tests for OAuth2 authorization flow."""

    def test_get_authorization_url(self, auth_client: DiscordClient) -> None:
        """Test OAuth2 authorization URL generation."""
        url, state = auth_client._get_authorization_url()

        assert "https://discord.com/api/oauth2/authorize" in url
        assert "response_type=code" in url
        assert f"client_id={auth_client.client_id}" in url
        # redirect_uri is URL-encoded in the actual URL
        assert "redirect_uri=" in url
        assert f"state={state}" in url
        assert len(state) > MIN_STATE_LENGTH  # State should be a random string

    def test_get_authorization_url_with_custom_state(self, auth_client: DiscordClient) -> None:
        """Test authorization URL with custom state."""
        custom_state = "my_custom_state"
        url, state = auth_client._get_authorization_url(state=custom_state)

        assert f"state={custom_state}" in url
        assert state == custom_state

    @patch("discord_client_impl.discord_impl.OAuth2Client")
    def test_exchange_code_for_token_success(
        self, mock_oauth_class: MagicMock, auth_client: DiscordClient
    ) -> None:
        """Test successful token exchange."""
        mock_response = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "token_type": "Bearer",
            "expires_in": 604800,
            "scope": "identify guilds",
        }

        mock_oauth_instance = MagicMock()
        mock_oauth_instance.fetch_token.return_value = mock_response
        mock_oauth_class.return_value = mock_oauth_instance

        result = auth_client._exchange_code_for_token("test_code")

        assert result["access_token"] == "new_access_token"
        assert result["refresh_token"] == "new_refresh_token"
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == DISCORD_TOKEN_EXPIRES_IN

    @patch("discord_client_impl.discord_impl.OAuth2Client")
    def test_exchange_code_for_token_failure(
        self, mock_oauth_class: MagicMock, auth_client: DiscordClient
    ) -> None:
        """Test token exchange with invalid code."""
        mock_oauth_instance = MagicMock()
        mock_oauth_instance.fetch_token.side_effect = Exception("Invalid grant")
        mock_oauth_class.return_value = mock_oauth_instance

        with pytest.raises(ValueError, match="Token exchange failed"):
            auth_client._exchange_code_for_token("invalid_code")

    @patch("discord_client_impl.discord_impl.OAuth2Client")
    def test_refresh_access_token_success(
        self, mock_oauth_class: MagicMock, auth_client: DiscordClient
    ) -> None:
        """Test successful token refresh."""
        mock_response = {
            "access_token": "refreshed_access_token",
            "refresh_token": "new_refresh_token",
            "token_type": "Bearer",
            "expires_in": 604800,
        }

        mock_oauth_instance = MagicMock()
        mock_oauth_instance.refresh_token.return_value = mock_response
        mock_oauth_class.return_value = mock_oauth_instance

        result = auth_client._refresh_access_token("old_refresh_token")

        assert result["access_token"] == "refreshed_access_token"
        assert result["refresh_token"] == "new_refresh_token"

    @patch("discord_client_impl.discord_impl.OAuth2Client")
    def test_refresh_access_token_failure(
        self, mock_oauth_class: MagicMock, auth_client: DiscordClient
    ) -> None:
        """Test token refresh with invalid refresh token."""
        mock_oauth_instance = MagicMock()
        mock_oauth_instance.refresh_token.side_effect = Exception("Invalid grant")
        mock_oauth_class.return_value = mock_oauth_instance

        with pytest.raises(ValueError, match="Token refresh failed"):
            auth_client._refresh_access_token("invalid_refresh_token")


class TestMessageOperations:
    """Tests for Discord message operations."""

    @respx.mock
    def test_get_messages_success(self, discord_client: DiscordClient) -> None:
        """Test getting messages from a channel."""
        mock_messages = [
            {
                "id": "123456",
                "channel_id": "789",
                "author": {"id": "111", "username": "TestUser"},
                "content": "Test message 1",
                "timestamp": "2025-01-01T00:00:00+00:00",
            },
            {
                "id": "123457",
                "channel_id": "789",
                "author": {"id": "222", "username": "AnotherUser"},
                "content": "Test message 2",
                "timestamp": "2025-01-01T00:01:00+00:00",
            },
        ]

        respx.get("https://discord.com/api/v10/channels/789/messages").mock(
            return_value=Response(200, json=mock_messages)
        )

        messages = discord_client.get_messages(channel_id="789", limit=10)

        assert len(messages) == EXPECTED_MESSAGE_COUNT
        assert messages[0].id == "123456"
        assert messages[0].content == "Test message 1"
        assert messages[0].sender_name == "TestUser"

    @respx.mock
    def test_get_messages_empty_channel(self, discord_client: DiscordClient) -> None:
        """Test getting messages from empty channel."""
        respx.get("https://discord.com/api/v10/channels/789/messages").mock(
            return_value=Response(200, json=[])
        )

        messages = discord_client.get_messages(channel_id="789")

        assert len(messages) == 0

    @respx.mock
    def test_get_message_by_id_success(self, discord_client: DiscordClient) -> None:
        """Test getting a specific message by ID."""
        mock_message = {
            "id": "123456",
            "channel_id": "789",
            "author": {"id": "111", "username": "TestUser"},
            "content": "Specific test message",
            "timestamp": "2025-01-01T00:00:00+00:00",
        }

        respx.get("https://discord.com/api/v10/channels/789/messages/123456").mock(
            return_value=Response(200, json=mock_message)
        )

        message = discord_client.get_message(channel_id="789", message_id="123456")

        assert message.id == "123456"
        assert message.content == "Specific test message"

    @respx.mock
    def test_send_message_success(self, discord_client: DiscordClient) -> None:
        """Test sending a message to a channel."""
        mock_response = {
            "id": "999",
            "channel_id": "789",
            "author": {"id": "111", "username": "BotUser"},
            "content": "Hello Discord!",
            "timestamp": "2025-01-01T00:00:00+00:00",
        }

        respx.post("https://discord.com/api/v10/channels/789/messages").mock(
            return_value=Response(200, json=mock_response)
        )

        result = discord_client.send_message(channel_id="789", content="Hello Discord!")

        assert result is True

    @respx.mock
    def test_send_message_failure(self, discord_client: DiscordClient) -> None:
        """Test sending message with error."""
        respx.post("https://discord.com/api/v10/channels/789/messages").mock(
            return_value=Response(403, json={"message": "Missing Access"})
        )

        with pytest.raises(MessageSendError, match="Failed to send message"):
            discord_client.send_message(channel_id="789", content="Test")

    @respx.mock
    def test_delete_message_success(self, discord_client: DiscordClient) -> None:
        """Test deleting a message."""
        respx.delete("https://discord.com/api/v10/channels/789/messages/123").mock(
            return_value=Response(204)
        )

        result = discord_client.delete_message(channel_id="789", message_id="123")

        assert result is True

    @respx.mock
    def test_delete_message_not_found(self, discord_client: DiscordClient) -> None:
        """Test deleting non-existent message raises MessageNotFoundError."""
        respx.delete("https://discord.com/api/v10/channels/789/messages/999").mock(
            return_value=Response(404, json={"message": "Unknown Message"})
        )

        with pytest.raises(MessageNotFoundError, match="Message 999 not found"):
            discord_client.delete_message(channel_id="789", message_id="999")


class TestChannelOperations:
    """Tests for Discord channel operations."""

    def test_get_channels_success(
        self, discord_client: DiscordClient, respx_mock: MockRouter
    ) -> None:
        """Test getting user's DM channels."""
        mock_channels = [
            {"id": "ch1", "name": "DM Channel 1", "type": 1},
            {"id": "ch2", "name": "DM Channel 2", "type": 1},
        ]

        respx_mock.get("https://discord.com/api/v10/users/@me/channels").mock(
            return_value=Response(200, json=mock_channels)
        )

        channels = list(discord_client.get_channels())

        assert len(channels) == EXPECTED_CHANNEL_COUNT
        assert channels[0].channel_id == "ch1"
        assert channels[1].channel_id == "ch2"

    @respx.mock
    def test_get_channel_by_id_success(self, discord_client: DiscordClient) -> None:
        """Test getting a specific channel by ID."""
        mock_channel = {
            "id": "123",
            "name": "test-channel",
            "type": 0,
        }

        respx.get("https://discord.com/api/v10/channels/123").mock(
            return_value=Response(200, json=mock_channel)
        )

        channel = discord_client.get_channel(channel_id="123")

        assert channel.channel_id == "123"
        assert channel.name == "test-channel"
        assert channel.channel_type == "text"

    def test_get_channel_not_found(
        self, discord_client: DiscordClient, respx_mock: MockRouter
    ) -> None:
        """Test getting non-existent channel."""
        respx_mock.get("https://discord.com/api/v10/channels/999").mock(
            return_value=Response(404, json={"message": "Unknown Channel"})
        )

        with pytest.raises(ChannelNotFoundError, match="Channel 999 not found"):
            discord_client.get_channel(channel_id="999")


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_unauthorized_request(
        self, discord_client: DiscordClient, respx_mock: MockRouter
    ) -> None:
        """Test handling of 401 Unauthorized."""
        respx_mock.get("https://discord.com/api/v10/users/@me/channels").mock(
            return_value=Response(401, json={"message": "401: Unauthorized"})
        )

        with pytest.raises(ValueError, match="Failed to retrieve channels"):
            list(discord_client.get_channels())

    @respx.mock
    def test_rate_limit_handling(self, discord_client: DiscordClient) -> None:
        """Test handling of 429 Rate Limit."""
        respx.get("https://discord.com/api/v10/channels/789/messages").mock(
            return_value=Response(429, json={"message": "Rate limited"})
        )

        with pytest.raises(ValueError, match="Failed to retrieve messages"):
            list(discord_client.get_messages(channel_id="789"))

    def test_operations_without_token(self) -> None:
        """Test that operations fail without access token."""
        client = DiscordClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

        with pytest.raises(AuthenticationError, match="Not authenticated"):
            list(client.get_channels())

    def test_get_message_http_error(
        self, discord_client: DiscordClient, respx_mock: MockRouter
    ) -> None:
        """Test get_message with HTTP error."""
        respx_mock.get("https://discord.com/api/v10/channels/ch1/messages/msg999").mock(
            return_value=Response(500, json={"message": "Internal Server Error"})
        )

        with pytest.raises(MessageNotFoundError, match="Failed to retrieve message"):
            discord_client.get_message(channel_id="ch1", message_id="msg999")

    def test_send_message_http_error(
        self, discord_client: DiscordClient, respx_mock: MockRouter
    ) -> None:
        """Test send_message with HTTP error."""
        respx_mock.post("https://discord.com/api/v10/channels/ch1/messages").mock(
            return_value=Response(500, json={"message": "Internal Server Error"})
        )

        with pytest.raises(MessageSendError, match="Failed to send message"):
            discord_client.send_message(channel_id="ch1", content="Test")

    def test_delete_message_http_error(
        self, discord_client: DiscordClient, respx_mock: MockRouter
    ) -> None:
        """Test delete_message with HTTP error raises exception."""
        respx_mock.delete("https://discord.com/api/v10/channels/ch1/messages/msg1").mock(
            return_value=Response(500, json={"message": "Internal Server Error"})
        )

        with pytest.raises(MessageDeleteError, match="Failed to delete message"):
            discord_client.delete_message(channel_id="ch1", message_id="msg1")

    def test_get_channel_http_error(
        self, discord_client: DiscordClient, respx_mock: MockRouter
    ) -> None:
        """Test get_channel with HTTP error."""
        respx_mock.get("https://discord.com/api/v10/channels/ch999").mock(
            return_value=Response(500, json={"message": "Internal Server Error"})
        )

        with pytest.raises(ChannelNotFoundError, match="Failed to retrieve channel"):
            discord_client.get_channel(channel_id="ch999")
