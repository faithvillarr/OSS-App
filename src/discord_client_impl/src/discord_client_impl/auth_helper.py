"""Authentication helper for Discord client using in-memory session-backed credentials."""

import logging
import os
from datetime import UTC, datetime

# Import session-backed credential helpers from the service package.
# The service package is available on the PYTHONPATH as `discord_client_service` when
# the workspace packages are installed in editable/development mode.
from discord_client_service.auth_session import (
    delete_credential,
    get_credential,
    set_credential,
)

from discord_client_impl.discord_impl import DiscordClient

LOGGER = logging.getLogger(__name__)

# central constant to avoid repeating string literals flagged by linters
BOT_TOKEN_TYPE = "Bot"  # noqa: S105


async def get_client_for_user(guild_id: str) -> DiscordClient:
    """Get Discord client for a specific guild with database-stored credentials.

    Args:
        guild_id: Unique guild identifier.

    Returns:
        DiscordClient: Configured Discord client with guild's access token.

    Raises:
        ValueError: If no credentials found for guild or credentials expired without refresh.

    """
    credentials = await get_credential(guild_id)

    if not credentials:
        error_msg = f"No credentials found for guild: {guild_id}"
        raise ValueError(error_msg)

    # If the stored credential exists but is not a Bot token, prefer using
    # the application bot token (DISCORD_BOT_TOKEN) for guild-level operations
    # because OAuth access tokens are not valid as bot tokens.
    # Prefer application-level bot token if present
    app_bot_token = os.environ.get("DISCORD_BOT_TOKEN")

    if credentials and str(credentials.get("token_type", "")).lower() != "bot" and app_bot_token:
        LOGGER.info(
            "Stored token for guild %s is not a bot token; falling back to application bot token",
            guild_id,
        )
        return DiscordClient(access_token=app_bot_token, token_type=BOT_TOKEN_TYPE)

    # Check if token is expired and needs refresh
    # If credential has expiry and it's expired, try refresh if refresh_token present
    if credentials and credentials.get("expires_at"):
        try:
            expires_iso = credentials.get("expires_at")
            expires_dt = (
                datetime.fromisoformat(expires_iso) if isinstance(expires_iso, str) else None
            )
            if expires_dt and expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=UTC)
            if expires_dt and datetime.now(UTC) >= expires_dt:
                LOGGER.info("Access token expired for guild %s, attempting refresh", guild_id)
                client = DiscordClient()
                try:
                    # Ensure we pass a str to _refresh_access_token (mypy requires str)
                    refresh_token = credentials.get("refresh_token")
                    if not refresh_token:
                        # Assign the message to a variable (avoid f-string in the raise
                        # expression and keep line lengths under the linter limit).
                        msg = (
                            "No refresh token available to refresh credentials "
                            f"for guild {guild_id}"
                        )
                        raise ValueError(msg)

                    # convert to str explicitly to satisfy the DiscordClient API contract
                    new_token_data = client._refresh_access_token(str(refresh_token))

                    # compute token_type safely and keep line lengths short
                    token_type_default = credentials.get("token_type", "Bearer")
                    token_type_val = new_token_data.get("token_type", token_type_default)

                    expires_at_val = new_token_data.get("expires_at")
                    expires_in_val = new_token_data.get("expires_in")
                    expires_val = (
                        expires_at_val if expires_at_val is not None else expires_in_val
                    )
                    scope_val = new_token_data.get("scope", credentials.get("scope"))

                    # Persist refreshed tokens in credential store
                    await set_credential(
                        guild_id,
                        {
                            "access_token": new_token_data["access_token"],
                            "refresh_token": new_token_data.get("refresh_token"),
                            "token_type": token_type_val,
                            "expires_at": expires_val,
                            "scope": scope_val,
                        },
                    )

                    return DiscordClient(
                        access_token=new_token_data["access_token"],
                        token_type=token_type_val,
                    )
                except Exception as e:
                    LOGGER.exception("Failed to refresh token for guild %s", guild_id)
                    msg = f"Failed to refresh expired token for guild {guild_id}: {e}"
                    raise ValueError(msg) from e
        except (ValueError, TypeError) as e:
            # If parsing fails, log and continue to use stored token if present
            LOGGER.debug("Failed to parse expires_at for guild %s: %s", guild_id, e)

    # Token is still valid, use it directly. Respect the stored token_type.
    return DiscordClient(
        access_token=credentials.get("access_token"),
        token_type=str(credentials.get("token_type", "Bearer")),
    )


async def get_bot_client_for_guild(guild_id: str) -> DiscordClient:
    """Return a DiscordClient configured with a bot token suitable for guild-level operations.

    Priority:
    1. Use application bot token from environment variable DISCORD_BOT_TOKEN if present.
    2. Otherwise, use stored credentials for the guild if they exist and are token_type 'bot'.
    3. Otherwise raise ValueError.

    """
    # 1) application-level bot token (recommended for bot installs)
    app_bot_token = os.environ.get("DISCORD_BOT_TOKEN")
    if app_bot_token:
        return DiscordClient(access_token=app_bot_token, token_type=BOT_TOKEN_TYPE)

    # 2) fallback to stored credentials if they are bot tokens
    credentials = await get_credential(guild_id)
    if credentials and str(credentials.get("token_type", "")).lower() == "bot":
        return DiscordClient(
            access_token=credentials.get("access_token"), token_type=BOT_TOKEN_TYPE
        )

    msg = (
        "No bot token available for guild. Set DISCORD_BOT_TOKEN or install the bot to the guild."
    )
    raise ValueError(msg)


async def store_user_credentials(
    guild_id: str,
    token_data: dict[str, object],
) -> None:
    """Store OAuth2 credentials for a guild in the database.

    Args:
        guild_id: Unique guild identifier.
        token_data: Token response from OAuth2 server containing:
                   - access_token: OAuth2 access token
                   - refresh_token: OAuth2 refresh token
                   - expires_in: Token expiry in seconds
                   - token_type: Token type (usually "Bot")
                   - scope: Granted scopes

    """
    # Persist credentials into in-memory credential store
    await set_credential(
        guild_id,
        {
            "access_token": str(token_data["access_token"]),
            "refresh_token": str(token_data.get("refresh_token")),
            "token_type": str(token_data.get("token_type", "Bearer")),
            # store expires_at as ISO string if provided, otherwise compute not implemented here
            "expires_at": token_data.get("expires_at") or None,
            "scope": str(token_data.get("scope", "")) if token_data.get("scope") else None,
        },
    )

    LOGGER.info("Stored credentials for guild: %s", guild_id)


async def delete_user_credentials(guild_id: str) -> bool:
    """Delete stored credentials for a guild.

    Args:
        guild_id: Unique guild identifier.

    Returns:
        True if credentials were deleted, False if not found.

    """
    deleted = await delete_credential(guild_id)

    if deleted:
        LOGGER.info("Deleted credentials for guild: %s", guild_id)
    else:
        LOGGER.warning("No credentials found to delete for guild: %s", guild_id)

    return deleted


async def check_user_authenticated(guild_id: str) -> bool:
    """Check if a guild has valid credentials stored.

    Args:
        guild_id: Unique guild identifier.

    Returns:
        True if guild has credentials (even if expired), False otherwise.

    """
    credentials = await get_credential(guild_id)
    return credentials is not None
