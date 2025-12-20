"""Additional tests for the DiscordClient implementation.

These tests are small unit tests for behavior of the client and are
annotated with simple docstrings and type hints to satisfy linting.
"""

from typing import Any, cast
from unittest.mock import MagicMock

import pytest
import respx
from httpx import Response

from discord_client_impl.discord_impl import DiscordClient


def test_get_authorization_url_without_client_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raise ValueError when DISCORD_CLIENT_ID is not configured in env."""
    # Ensure no env var
    monkeypatch.delenv("DISCORD_CLIENT_ID", raising=False)
    client = DiscordClient(client_id=None, client_secret=None)

    with pytest.raises(ValueError, match="DISCORD_CLIENT_ID not configured"):
        client._get_authorization_url()


def test_update_http_client_sets_headers() -> None:
    """Ensure _update_http_client sets the Authorization header correctly."""
    client = DiscordClient(client_id="cid", client_secret="cs", access_token=None, token_type="Bot")
    # assign access token and call update
    client.access_token = "newtoken"
    client._update_http_client()

    assert client._http_client.headers.get("Authorization") == f"{client.token_type} newtoken"


@respx.mock
def test_leave_guild_success() -> None:
    """Leaving a guild returns True on HTTP 204."""
    client = DiscordClient(client_id="cid", client_secret="cs", access_token="t")
    respx.delete("https://discord.com/api/v10/users/@me/guilds/g1").mock(return_value=Response(204))

    assert client.leave_guild("g1") is True


@respx.mock
def test_leave_guild_failure() -> None:
    """Non-2xx response when leaving a guild raises ValueError."""
    client = DiscordClient(client_id="cid", client_secret="cs", access_token="t")
    respx.delete("https://discord.com/api/v10/users/@me/guilds/g1").mock(return_value=Response(500))

    with pytest.raises(ValueError, match="Failed to leave guild"):
        client.leave_guild("g1")


@respx.mock
def test_get_guild_channels_success() -> None:
    """get_guild_channels yields Channel objects for the guild on success."""
    client = DiscordClient(client_id="cid", client_secret="cs", access_token="t")
    mock_channels = [{"id": "c1", "name": "A", "type": 0}, {"id": "c2", "name": "B", "type": 0}]
    url = "https://discord.com/api/v10/guilds/g1/channels"
    respx.get(url).mock(return_value=Response(200, json=mock_channels))

    channels = list(client.get_guild_channels("g1"))
    assert len(channels) == len(mock_channels)
    assert channels[0].channel_id == "c1"


@respx.mock
def test_get_guild_channels_failure() -> None:
    """get_guild_channels raises ValueError on non-2xx HTTP response."""
    client = DiscordClient(client_id="cid", client_secret="cs", access_token="t")
    respx.get("https://discord.com/api/v10/guilds/g1/channels").mock(return_value=Response(500))

    with pytest.raises(ValueError, match="Failed to retrieve guild channels"):
        list(client.get_guild_channels("g1"))


def test_context_manager_closes_http_client() -> None:
    """Using the client as a context manager closes the underlying HTTP client."""
    client = DiscordClient(client_id="cid", client_secret="cs", access_token="t")
    # patch the underlying client's close (cast to Any to satisfy type checker)
    cast("Any", client._http_client).close = MagicMock()

    with client:
        pass
    # `close` is declared as Callable[[], None] on the http client, so mypy
    # doesn't know about the MagicMock attributes. Cast to MagicMock to
    # access `.called` without a type error.
    assert cast("MagicMock", cast("Any", client._http_client).close).called
