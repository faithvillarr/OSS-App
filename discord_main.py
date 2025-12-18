"""Simple demo entrypoint for the chat API using Discord as the backend.

This script:
1. Creates a ChatClient using chat_client_impl (which adapts discord_api to chat_api).
2. Sends a test message to the configured channel.
3. Fetches and prints a few recent messages from that channel.

Usage:
    export DISCORD_BOT_TOKEN="your_bot_token"
    uv run python discord_main.py
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Final

from dotenv import load_dotenv

import chat_client_impl  # noqa: F401
import chat_api


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        logger.error("Environment variable %s is required but not set.", name)
        raise SystemExit(1)
    return value


def main() -> None:
    """Run a small end-to-end demo using the chat_api interface with Discord backend."""
    # Load environment variables from a local .env file if present.
    # This allows you to configure DISCORD_* values without exporting them manually.
    load_dotenv()

    # These IDs must come from your Discord server:
    # - GUILD_ID: right-click your server (with Developer Mode on) -> Copy Server ID
    # - CHANNEL_ID: right-click a text channel -> Copy Channel ID
    guild_id: Final[str] = os.getenv("DISCORD_GUILD_ID", "")
    channel_id: Final[str] = os.getenv("DISCORD_CHANNEL_ID", "")

    if not guild_id or not channel_id:
        logger.error(
            "Please set DISCORD_GUILD_ID and DISCORD_CHANNEL_ID in your environment "
            "before running this script."
        )
        logger.info("Example:")
        logger.info("  export DISCORD_GUILD_ID='your_guild_id'")
        logger.info("  export DISCORD_CHANNEL_ID='your_channel_id'")
        raise SystemExit(1)

    # Ensure the bot token is set (get_client will read it from environment)
    _require_env("DISCORD_BOT_TOKEN")

    logger.info("Creating ChatClient using bot token from DISCORD_BOT_TOKEN...")
    client = chat_api.get_client()

    logger.info("=== Sending a test message to channel %s ===", channel_id)
    message_content = "Hello from discord_main.py demo!"
    sent = client.send_message(channel_id=channel_id, content=message_content)
    logger.info("Send message call succeeded: %s", sent)

    logger.info("=== Fetching recent messages from channel %s ===", channel_id)
    messages = list(client.get_messages(channel_id=channel_id, limit=5))

    if not messages:
        logger.info("No messages returned from Discord for this channel.")
        return

    for m in messages:
        logger.info("[%s] %s", m.id, m.content)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
