> ### Team 7 Discord Implementation
>
> This repo is completely copied from Team 7's Discord implementation with no changes. There implemenation still services our implementation. 

# Discord Client Implementation

Discord implementation of the `discord_api` contract with OAuth2 and bot-token support.

This README reflects the current implementation in `src/discord_client_impl` (OAuth helpers, HTTP wrappers
against Discord REST API v10, and small adapter objects for messages/channels).

## Highlights / What changed

- The client supports both OAuth2 access tokens and application/bot tokens. A default token type of
    `Bot` is used for backwards compatibility, but `Bearer` is supported for OAuth flows.
- OAuth helper utilities live in `auth_helper.py` and provide helpers to store/refresh credentials
    (backed by the in-memory session store used in the dev environment).
- The package exposes adapter classes `DiscordMessage` and `DiscordChannel` for the abstract `discord_api`
    message/channel interfaces.
- Importing `discord_client_impl` auto-registers the implementation with `discord_api` (see note below).

## Features

- OAuth2 authentication (authorization code exchange + refresh)
- Support for application bot tokens (recommended for bot installs)
- Token management: access token, refresh token, token type, and expiry handling
- Discord REST API v10 coverage for common chat operations:
    - send, retrieve, delete messages
    - list DM channels, get channel info, list guild channels
    - leave a guild (bot token required)
- Small, typed adapters: `DiscordMessage`, `DiscordChannel`
- Test coverage with `pytest` and `respx` request mocking

## Environment variables

These environment variables are consulted when creating a `DiscordClient` without explicit constructor args:

- DISCORD_CLIENT_ID: OAuth2 application client id (required for authorization URL / code exchange)
- DISCORD_CLIENT_SECRET: OAuth2 application client secret (required for token exchange / refresh)
- DISCORD_REDIRECT_URI: OAuth2 redirect URI used when building the authorization URL
- DISCORD_BOT_TOKEN: (optional) application-level bot token; preferred for guild-level bot operations
- DISCORD_DEFAULT_TOKEN_TYPE: (optional) default token type to use in Authorization header (defaults to "Bot")

Example (bash):

```bash
export DISCORD_CLIENT_ID=your-client-id
export DISCORD_CLIENT_SECRET=your-client-secret
export DISCORD_REDIRECT_URI=http://localhost:8001/auth/callback
export DISCORD_BOT_TOKEN=your_bot_token  # optional
export DISCORD_DEFAULT_TOKEN_TYPE=Bot    # optional, defaults to "Bot"
```

## OAuth2 / Bot token notes

- The package requests scopes for interactive installs and reading messages: `identify`, `guilds`, `messages.read`.
- For bot installs (adding a bot to a guild), the implementation also includes a `bot`/permissions flow and
    requests permission bits appropriate for viewing channels, sending messages and reading message history.
    The code computes a permission integer by combining constants:

    - view_channel = 0x00000400 (1024)
    - send_messages = 0x00000800 (2048)
    - read_message_history = 0x00010000 (65536)
    - combined permissions value used in the authorization URL = 68608

## Public API and usage

Note: Several helpers in the implementation are implemented as "internal" methods (prefixed with an underscore)
because they closely map to the OAuth flow. The tests rely on them directly; you can use them in your
integration code but consider wrapping them if you want a strictly public surface.

Direct usage with a known access token (bot or bearer):

```python
from discord_client_impl import DiscordClient

# With an existing token (bot or bearer). token_type defaults to "Bot" unless overridden.
client = DiscordClient(access_token="your_access_token", token_type="Bot")

# Send a message
message = client.send_message(channel_id="123456", content="Hello!")

# Get recent messages
messages = list(client.get_messages(channel_id="123456", max_results=10))
```

OAuth2 flow (authorization code exchange):

```python
from discord_client_impl import DiscordClient

# Initialize without access_token to build auth URLs
client = DiscordClient(client_id="your_client_id", client_secret="your_client_secret",
                                             redirect_uri="http://localhost:8001/auth/callback")

# NOTE: the implementation currently exposes these helpers as underscore-prefixed methods
# (they match the test harness). Use them directly or implement a small wrapper in your
# application to manage state and credential persistence.
auth_url, state = client._get_authorization_url()  # redirect user to auth_url

# After the callback: exchange the code for tokens
# token_data contains access_token, refresh_token, token_type, expires_in, etc.
token_data = client._exchange_code_for_token(code="code_from_callback")

# You may persist token_data using the helper in auth_helper (store_user_credentials)
from discord_client_impl.auth_helper import store_user_credentials
import asyncio
asyncio.run(store_user_credentials(guild_id="<guild-id>", token_data=token_data))

# Create a client with the token
client = DiscordClient(access_token=token_data["access_token"], token_type=token_data.get("token_type","Bearer"))
```

Using the abstract `discord_api` registration (package auto-registers on import):

```python
import discord_client_impl  # side-effect: registers Discord implementations
import discord_api

client = discord_api.get_client(user_id="user123")
message = client.send_message(channel_id="123456", content="Hello via abstract API")
```

## auth_helper utilities

`auth_helper.py` contains async helpers to integrate with the in-memory credential store used by the service
package in development. Key helpers:

- `get_client_for_user(guild_id)` - returns a `DiscordClient` configured with the stored access token (refreshes when expired)
- `get_bot_client_for_guild(guild_id)` - returns a `DiscordClient` using the application-level bot token or stored bot token
- `store_user_credentials(guild_id, token_data)` - persist OAuth token data for a guild
- `delete_user_credentials(guild_id)` - remove stored credentials
- `check_user_authenticated(guild_id)` - check whether credentials exist for a guild

These helpers make it straightforward to wire the OAuth flow into a small web service that handles the
authorization callback and persists tokens.

## Packaging and typing

- The package includes a `py.typed` marker so consumers can benefit from type hints.
- The package is configured with `hatchling` in `pyproject.toml` and lists `httpx` and `authlib` as runtime deps.

## Notes

- Several OAuth helpers are currently implemented as internal methods (leading underscore).
- Credentials are persisted using the in-memory session-backed helpers during development.
