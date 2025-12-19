"""Constantly running service that polls Discord for new messages and responds."""

import logging
import os
import sys
import time
from typing import Final

import chat_api
import chat_client_impl  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Maximum length for message content in logs
MAX_LOG_CONTENT_LENGTH = 50

def _determine_bot_user_id(client: chat_api.ChatInterface, channel_id: str) -> str | None:
    """Determine the bot's user ID by sending a test message.

    Args:
        client: The chat client to use.
        channel_id: The channel ID to send the test message to.

    Returns:
        The bot's user ID if found, None otherwise.

    """
    bot_user_id: str | None = None
    try:
        test_response = "___BOT_ID_TEST___"
        if client.send_message(channel_id=channel_id, content=test_response):
            # Fetch messages to find the one we just sent
            time.sleep(0.2)  # Small delay to ensure message is available
            test_messages = client.get_messages(channel_id=channel_id, limit=3)
            for msg in test_messages:
                if msg.content == test_response:
                    bot_user_id = msg.sender_id
                    logger.info("Bot user ID determined: %s", bot_user_id)
                    # Delete the test message
                    client.delete_message(channel_id=channel_id, message_id=msg.id)
                    break
        if not bot_user_id:
            logger.warning("Could not determine bot user ID - will filter by message content instead")
    except Exception:
        logger.exception("Failed to determine bot user ID - will filter by message content instead")

    return bot_user_id


def _initialize_seen_messages(
    client: chat_api.ChatInterface,
    channel_id: str,
) -> set[str]:
    """Initialize the set of seen message IDs by fetching current messages.

    This ensures we don't respond to messages that existed before startup.

    Args:
        client: The chat client to use.
        channel_id: The channel ID to fetch messages from.
        message_check_limit: Maximum number of messages to fetch.

    Returns:
        Set of message IDs that have been seen.

    """
    seen_message_ids: set[str] = set()
    message_check_limit: Final[int] = 5

    try:
        initial_messages = client.get_messages(channel_id=channel_id, limit=message_check_limit)
        for msg in initial_messages:
            seen_message_ids.add(msg.id)
        logger.info("Initialization complete: marked %d existing messages as seen", len(initial_messages))
    except Exception:
        logger.exception("Failed to fetch initial messages")
        raise

    return seen_message_ids


def _filter_new_messages(
    messages: list[chat_api.Message],
    seen_message_ids: set[str],
    bot_user_id: str | None,
) -> list[chat_api.Message]:
    """Filter messages to find new ones that haven't been seen before.

    Args:
        messages: List of messages to filter.
        seen_message_ids: Set of message IDs that have already been seen.
        bot_user_id: The bot's user ID to filter out bot messages.

    Returns:
        List of new messages that should be processed.

    """
    return [
        msg
        for msg in messages
        if msg.id not in seen_message_ids
        and (bot_user_id is None or msg.sender_id != bot_user_id)
        and msg.content != "What a cool message!"  # Filter our own responses by content
    ]


def _process_new_message(
    client: chat_api.ChatInterface,
    msg: chat_api.Message,
    channel_id: str,
    seen_message_ids: set[str],
) -> None:
    """Process a single new message by responding to it.

    Args:
        client: The chat client to use.
        msg: The message to process.
        channel_id: The channel ID to send the response to.
        seen_message_ids: Set of seen message IDs to update.

    """
    msg_id = msg.id

    # Double-check: if this message ID is somehow in seen_message_ids, skip it
    if msg_id in seen_message_ids:
        return

    logger.info("New message from sender=%s: '%s'", msg.sender_id, msg.content)

    # Respond to the new message
    response = "What a cool message!"
    success = client.send_message(channel_id=channel_id, content=response)
    if not success:
        logger.error("Failed to send response to message %s", msg_id)

    # Mark message as seen immediately
    seen_message_ids.add(msg_id)


def _process_new_messages(
    client: chat_api.ChatInterface,
    new_messages: list[chat_api.Message],
    channel_id: str,
    seen_message_ids: set[str],
    message_check_limit: int,
) -> list[chat_api.Message]:
    """Process all new messages and re-fetch messages to update our view.

    Args:
        client: The chat client to use.
        new_messages: List of new messages to process.
        channel_id: The channel ID.
        seen_message_ids: Set of seen message IDs to update.
        message_check_limit: Maximum number of messages to fetch.

    Returns:
        Updated list of messages after processing.

    """
    logger.info("Found %d new message(s)", len(new_messages))

    for msg in new_messages:
        _process_new_message(client, msg, channel_id, seen_message_ids)

    # Re-fetch messages after sending response to update our view
    # This ensures our own response and any other new messages are tracked
    return client.get_messages(channel_id=channel_id, limit=message_check_limit)


def _poll_cycle(
    client: chat_api.ChatInterface,
    channel_id: str,
    message_check_limit: int,
    seen_message_ids: set[str],
    bot_user_id: str | None,
) -> None:
    """Execute a single polling cycle.

    Args:
        client: The chat client to use.
        channel_id: The channel ID to poll.
        message_check_limit: Maximum number of messages to fetch.
        seen_message_ids: Set of seen message IDs to update.
        bot_user_id: The bot's user ID to filter out bot messages.

    """
    # Fetch the most recent messages
    messages = client.get_messages(channel_id=channel_id, limit=message_check_limit)

    # Check for new messages
    new_messages = _filter_new_messages(messages, seen_message_ids, bot_user_id)

    if new_messages:
        # Process new messages and re-fetch to update our view
        messages = _process_new_messages(
            client, new_messages, channel_id, seen_message_ids, message_check_limit
        )

    # Update seen set with all current messages (in case we missed some)
    for msg in messages:
        seen_message_ids.add(msg.id)


def _run_polling_loop(
    client: chat_api.ChatInterface,
    channel_id: str,
    seen_message_ids: set[str],
    bot_user_id: str | None,
) -> None:
    """Run the main polling loop.

    Args:
        client: The chat client to use.
        channel_id: The channel ID to poll.
        polling_interval: Time to wait between polls in seconds.
        message_check_limit: Maximum number of messages to fetch per poll.
        seen_message_ids: Set of seen message IDs to track.
        bot_user_id: The bot's user ID to filter out bot messages.

    """
    logger.info("Starting polling loop...")
    poll_count = 0

    # Default polling interval and message check limit
    polling_interval: Final[float] = 2
    message_check_limit: Final[int] = 5

    try:
        while True:
            poll_count += 1
            try:
                _poll_cycle(client, channel_id, message_check_limit, seen_message_ids, bot_user_id)
                time.sleep(polling_interval)
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                raise
            except Exception:
                logger.exception("Error during polling cycle #%d", poll_count)
                # Continue polling even if there's an error
                time.sleep(polling_interval)
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        sys.exit(0)
    except Exception:
        logger.exception("Fatal error")
        sys.exit(1)


def main() -> None:
    """Run the Discord polling service."""
    # Start up the service
    channel_id = os.getenv("DISCORD_CHANNEL_ID")
    if not channel_id:
        logger.error("DISCORD_CHANNEL_ID environment variable is not set")
        raise SystemExit(1)

    client = chat_api.get_client()
    bot_user_id = _determine_bot_user_id(client, channel_id) # Filter out bot messages
    seen_message_ids = _initialize_seen_messages(client, channel_id) # Initialize seen messages set

    # Small delay to ensure initialization is complete before starting to poll
    time.sleep(0.1)

    # Main polling loop
    _run_polling_loop(
        client, channel_id, seen_message_ids, bot_user_id
    )


if __name__ == "__main__":
    main()
