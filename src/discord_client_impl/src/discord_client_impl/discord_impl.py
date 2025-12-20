"""Discord client implementation with OAuth2 authentication."""

import logging
import os
from collections.abc import Iterator
from enum import IntEnum
from typing import Any

import httpx
from authlib.integrations.httpx_client import OAuth2Client  # type: ignore[import-untyped]
from discord_api.client import ChatInterface
from discord_api.exceptions import (
    AuthenticationError,
    ChannelNotFoundError,
    MessageDeleteError,
    MessageNotFoundError,
    MessageSendError,
)
from discord_api.message import Channel, Message

from discord_client_impl.message_impl import DiscordChannel, DiscordMessage

logger = logging.getLogger(__name__)


class HTTPStatus(IntEnum):
    """HTTP status codes used in Discord API responses."""

    NOT_FOUND = 404


class DiscordClient(ChatInterface):  # type: ignore[misc]
    """Discord implementation of chat client with OAuth2 support."""

    DISCORD_API_BASE = "https://discord.com/api/v10"
    OAUTH2_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
    OAUTH2_TOKEN_URL = "https://discord.com/api/oauth2/token"

    def __init__(
        self,
        access_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        token_type: str | None = None,
    ) -> None:
        """Initialize Discord client with OAuth2 credentials.

        Args:
            access_token: Discord OAuth2 access token (if already authenticated).
            client_id: Discord application client ID (for OAuth flow).
            client_secret: Discord application client secret (for OAuth flow).
            redirect_uri: OAuth2 redirect URI (for OAuth flow).
            token_type: Authorization header token type to use when sending requests
                (e.g. "Bot" or "Bearer"). If not provided, the environment
                variable `DISCORD_DEFAULT_TOKEN_TYPE` is consulted or defaults
                to "Bot" for backwards compatibility.

        """
        self.client_id = client_id or os.environ.get("DISCORD_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("DISCORD_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.environ.get(
            "DISCORD_REDIRECT_URI", "http://localhost:8001/auth/callback"
        )
        self.access_token = access_token
        # Create HTTP client
        # Token type controls the Authorization header verb (Bearer vs Bot)
        # If not provided, default to Bot for backwards compatibility with previous changes.
        self.token_type = token_type or os.environ.get("DISCORD_DEFAULT_TOKEN_TYPE", "Bot")

        # Create HTTP client
        if self.access_token:
            self._http_client: httpx.Client = httpx.Client(
                base_url=self.DISCORD_API_BASE,
                headers={"Authorization": f"{self.token_type} {self.access_token}"},
                timeout=30.0,
            )
        else:
            self._http_client = httpx.Client(
                base_url=self.DISCORD_API_BASE,
                timeout=30.0,
            )

        logger.info("Discord client initialized")

    def _get_authorization_url(self, state: str | None = None) -> tuple[str, str]:
        """Generate OAuth2 authorization URL.

        Args:
            state: Optional state parameter for CSRF protection.

        Returns:
            Tuple of (authorization_url, state).

        Raises:
            ValueError: If client_id is not configured.

        """
        if not self.client_id:
            raise ValueError("DISCORD_CLIENT_ID not configured")

        oauth_client = OAuth2Client(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
        )

        # Discord requires specific scopes for reading/sending messages.
        # Requested scopes: identity, guilds, messages.read and bot.
        scopes = ["identify", "guilds", "messages.read", "bot"]

        # For bot installs, request the specific permission bits the bot needs.
        # Use named constants for clarity (lowercase to satisfy local variable naming):
        # view_channel, send_messages, read_message_history.
        view_channel = 0x00000400  # 1024
        send_messages = 0x00000800  # 2048
        read_message_history = 0x00010000  # 65536

        permissions = view_channel | send_messages | read_message_history  # = 68608

        # Integration type: Guild Install (this authorizes the bot for a guild).
        # Build authorization URL. Include explicit response_type to make intent clear.
        authorization_url, state_value = oauth_client.create_authorization_url(
            self.OAUTH2_AUTHORIZE_URL,
            scope=" ".join(scopes),
            state=state,
            permissions=permissions,
            response_type="code",
            prompt="consent",
        )

        return authorization_url, state_value

    def _exchange_code_for_token(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback.

        Returns:
            Token response containing access_token, refresh_token, etc.

        Raises:
            ValueError: If credentials are not configured or exchange fails.

        """
        if not self.client_id or not self.client_secret:
            raise ValueError("DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET required")

        oauth_client = OAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
        )

        try:
            token = oauth_client.fetch_token(
                self.OAUTH2_TOKEN_URL,
                code=code,
                grant_type="authorization_code",
            )
            self.access_token = token.get("access_token")  # type: ignore[assignment]
            self._update_http_client()
            return dict(token)  # type: ignore[arg-type]
        except Exception as e:
            logger.exception("Failed to exchange code for token")
            raise ValueError(f"Token exchange failed: {e}") from e

    def _refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh the access token using a refresh token.

        Args:
            refresh_token: The refresh token from previous authentication.

        Returns:
            New token response.

        Raises:
            ValueError: If credentials are not configured or refresh fails.

        """
        if not self.client_id or not self.client_secret:
            raise ValueError("DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET required")

        oauth_client = OAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
        )

        try:
            token = oauth_client.refresh_token(
                self.OAUTH2_TOKEN_URL,
                refresh_token=refresh_token,
                grant_type="refresh_token",
            )
            self.access_token = token.get("access_token")  # type: ignore[assignment]
            self._update_http_client()
            return dict(token)  # type: ignore[arg-type]
        except Exception as e:
            logger.exception("Failed to refresh token")
            raise ValueError(f"Token refresh failed: {e}") from e

    def _update_http_client(self) -> None:
        """Update HTTP client with new access token."""
        if self.access_token:
            self._http_client.close()
            self._http_client = httpx.Client(
                base_url=self.DISCORD_API_BASE,
                headers={"Authorization": f"{self.token_type} {self.access_token}"},
                timeout=30.0,
            )

    def _ensure_authenticated(self) -> None:
        """Ensure client has valid access token.

        Raises:
            AuthenticationError: If not authenticated.

        """
        if not self.access_token:
            raise AuthenticationError("Not authenticated. Call exchange_code_for_token first.")

    def get_message(self, channel_id: str, message_id: str) -> Message:
        """Retrieve a specific message from a channel.

        Args:
            channel_id: The ID of the channel containing the message.
            message_id: The ID of the message to retrieve.

        Returns:
            Message: The requested message.

        Raises:
            AuthenticationError: If not authenticated.
            MessageNotFoundError: If the message is not found.
            ChatClientError: If the request fails for other reasons.

        """
        self._ensure_authenticated()

        try:
            response = self._http_client.get(f"/channels/{channel_id}/messages/{message_id}")
            response.raise_for_status()
            return DiscordMessage(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                raise MessageNotFoundError(
                    f"Message {message_id} not found in channel {channel_id}"
                ) from e
            logger.exception("Failed to get message")
            raise MessageNotFoundError(f"Failed to retrieve message: {e}") from e
        except Exception as e:
            logger.exception("Failed to get message")
            raise MessageNotFoundError(f"Failed to retrieve message: {e}") from e

    def get_messages(self, channel_id: str, limit: int = 10) -> list[Message]:
        """Retrieve recent messages from a channel.

        Args:
            channel_id: The ID of the channel to retrieve messages from.
            limit: Maximum number of messages to retrieve (default: 10, max: 100).

        Returns:
            list[Message]: An iterator of messages from the channel.

        """
        self._ensure_authenticated()

        # Discord API limits to 100 messages per request
        limit = min(limit, 100)

        try:
            response = self._http_client.get(
                f"/channels/{channel_id}/messages",
                params={"limit": limit},
            )
            response.raise_for_status()
            messages = response.json()
            return [DiscordMessage(msg_data) for msg_data in messages]

        except httpx.HTTPStatusError as e:
            logger.exception("Failed to get messages")
            raise ValueError(f"Failed to retrieve messages: {e}") from e
        except Exception as e:
            logger.exception("Failed to get messages")
            raise ValueError(f"Failed to retrieve messages: {e}") from e

    def send_message(self, channel_id: str, content: str) -> bool:
        """Send a message to a channel.

        Args:
            channel_id: The ID of the channel to send the message to.
            content: The text content of the message.

        Returns:
            bool: True if the message was successfully sent.

        Raises:
            AuthenticationError: If not authenticated.
            MessageSendError: If the message could not be sent.

        """
        self._ensure_authenticated()

        if not content.strip():
            raise MessageSendError("Message content cannot be empty")

        try:
            response = self._http_client.post(
                f"/channels/{channel_id}/messages",
                json={"content": content},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.exception("Failed to send message")
            raise MessageSendError(f"Failed to send message: {e}") from e
        except Exception as e:
            logger.exception("Failed to send message")
            raise MessageSendError(f"Failed to send message: {e}") from e

    def delete_message(self, channel_id: str, message_id: str) -> bool:
        """Delete a message from a channel.

        Args:
            channel_id: The ID of the channel containing the message.
            message_id: The ID of the message to delete.

        Returns:
            bool: True if the message was successfully deleted.

        Raises:
            AuthenticationError: If not authenticated.
            MessageNotFoundError: If the message does not exist.
            MessageDeleteError: If deletion fails for other reasons.

        """
        self._ensure_authenticated()

        try:
            response = self._http_client.delete(f"/channels/{channel_id}/messages/{message_id}")
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                raise MessageNotFoundError(
                    f"Message {message_id} not found in channel {channel_id}"
                ) from e
            logger.exception("Failed to delete message")
            raise MessageDeleteError(f"Failed to delete message: {e}") from e
        except Exception as e:
            logger.exception("Failed to delete message")
            raise MessageDeleteError(f"Failed to delete message: {e}") from e

    def get_channels(self) -> Iterator[Channel]:
        """Retrieve all accessible channels.

        Note: This returns DM channels for the authenticated user.
        For guild channels, use get_guild_channels().

        Returns:
            Iterator[Channel]: An iterator of available DM channels.

        """
        self._ensure_authenticated()

        try:
            # Get user's DM channels
            response = self._http_client.get("/users/@me/channels")
            response.raise_for_status()
            channels = response.json()

            for channel_data in channels:
                yield DiscordChannel(channel_data)

        except httpx.HTTPStatusError as e:
            logger.exception("Failed to get channels")
            raise ValueError(f"Failed to retrieve channels: {e}") from e
        except Exception as e:
            logger.exception("Failed to get channels")
            raise ValueError(f"Failed to retrieve channels: {e}") from e

    def get_channel(self, channel_id: str) -> Channel:
        """Retrieve information about a specific channel.

        Args:
            channel_id: The ID of the channel to retrieve.

        Returns:
            Channel: The requested channel.

        Raises:
            AuthenticationError: If not authenticated.
            ChannelNotFoundError: If the channel is not found.

        """
        self._ensure_authenticated()

        try:
            response = self._http_client.get(f"/channels/{channel_id}")
            response.raise_for_status()
            return DiscordChannel(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                raise ChannelNotFoundError(f"Channel {channel_id} not found") from e
            logger.exception("Failed to get channel")
            raise ChannelNotFoundError(f"Failed to retrieve channel: {e}") from e
        except Exception as e:
            logger.exception("Failed to get channel")
            raise ChannelNotFoundError(f"Failed to retrieve channel: {e}") from e

    def close(self) -> None:
        """Close the HTTP client."""
        self._http_client.close()

    def get_guild_channels(self, guild_id: str) -> Iterator[Channel]:
        """Retrieve channels for a specific guild."""
        self._ensure_authenticated()

        try:
            response = self._http_client.get(f"/guilds/{guild_id}/channels")
            response.raise_for_status()
            channels = response.json()

            for channel_data in channels:
                yield DiscordChannel(channel_data)

        except httpx.HTTPStatusError as e:
            logger.exception("Failed to get guild channels")
            raise ValueError(f"Failed to retrieve guild channels: {e}") from e
        except Exception as e:
            logger.exception("Failed to get guild channels")
            raise ValueError(f"Failed to retrieve guild channels: {e}") from e

    def __enter__(self) -> "DiscordClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()

    def leave_guild(self, guild_id: str) -> bool:
        """Make the bot leave a guild.

        Returns True on success, raises an exception on failure.
        """
        # For bot token clients, DELETE /users/@me/guilds/{guild_id} removes the
        # current user (bot) from the guild.
        self._ensure_authenticated()

        try:
            response = self._http_client.delete(f"/users/@me/guilds/{guild_id}")
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.exception("Failed to leave guild %s", guild_id)
            raise ValueError(f"Failed to leave guild {guild_id}: {e}") from e
        except Exception as e:
            logger.exception("Failed to leave guild %s", guild_id)
            raise ValueError(f"Failed to leave guild {guild_id}: {e}") from e
