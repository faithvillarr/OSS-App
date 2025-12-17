"""Background message polling service for Slack channels."""

import asyncio
import logging
import os
import time

from slack_sdk import WebClient as SlackWebClient
from slack_sdk.errors import SlackApiError

from chat_service.command_parser import CommandParser
from chat_service.dependencies import get_bot_token
from chat_service.tickets_integration import TicketsIntegration

logger = logging.getLogger(__name__)

# Bot user IDs in Slack typically start with 'B' and are 10 characters
BOT_USER_ID_LENGTH = 10

# Global state for tracking last processed timestamps per channel
_last_processed_ts: dict[str, float] = {}

# Global flag to control polling
_polling_active = False
_polling_task: asyncio.Task | None = None

_tickets_integration = TicketsIntegration()


def _get_monitored_channels() -> list[str]:
    """Get list of channels to monitor from environment variable.

    Returns:
        List of channel IDs to monitor.
    """
    channels_str = os.environ.get("MONITORED_CHANNELS", "")
    if not channels_str:
        logger.warning("MONITORED_CHANNELS not set, no channels will be monitored")
        return []

    # Split by comma and strip whitespace
    return [ch.strip() for ch in channels_str.split(",") if ch.strip()]


def _process_message(
    client: SlackWebClient,
    channel_id: str,
    message_text: str,
    message_ts: str,
    message_user: str,
) -> None:
    """Process a single message: check for ticket commands and respond.

    Args:
        client: Slack WebClient instance.
        channel_id: The channel ID where the message was posted.
        message_text: The message text content.
        message_ts: The message timestamp (used as ID).
        message_user: The user ID who sent the message.
    """
    # Skip if message is from a bot (to avoid infinite loops)
    if message_user.startswith("B") and len(message_user) == BOT_USER_ID_LENGTH:
        logger.debug("Skipping bot message from %s", message_user)
        return

    # Check if message contains a ticket command
    if not CommandParser.is_ticket_command(message_text):
        logger.debug("Message does not contain ticket command, skipping")
        return

    logger.info(
        "Processing ticket command in message %s from user %s in channel %s",
        message_ts,
        message_user,
        channel_id,
    )

    # Parse and execute command
    parsed = CommandParser.parse_command(message_text)
    if not parsed:
        logger.warning("Failed to parse command from message: %s", message_text)
        return

    command_name, args = parsed
    success, response_message, _ = _tickets_integration.execute_command(
        command_name, args
    )

    # Create response message
    response_content = response_message
    if not success:
        response_content = f"Error: {response_message}"

    # Post response to Slack
    try:
        client.chat_postMessage(channel=channel_id, text=response_content)
        logger.info(
            "Posted response to channel %s for message %s",
            channel_id,
            message_ts,
        )
    except SlackApiError as e:
        logger.error(
            "Failed to post response to Slack channel %s: %s",
            channel_id,
            e,
        )


async def _poll_channel(channel_id: str, bot_token: str) -> None:
    """Poll a single channel for new messages.

    Args:
        channel_id: The channel ID to poll.
        bot_token: Bot token for Slack API.
    """
    client = SlackWebClient(token=bot_token)

    try:
        # Get last processed timestamp for this channel
        last_ts = _last_processed_ts.get(channel_id, time.time())

        # Fetch recent messages from Slack
        # Use oldest parameter to get messages newer than last_ts
        resp = client.conversations_history(
            channel=channel_id,
            limit=50,  # Fetch up to 50 messages
            oldest=str(last_ts),  # Only get messages newer than last processed
        )

        messages = resp.get("messages", [])
        if not messages:
            logger.debug("No new messages in channel %s", channel_id)
            return

        # Process messages in reverse order (oldest first)
        # This ensures we process them chronologically
        messages.reverse()

        newest_ts = last_ts
        for msg in messages:
            msg_ts_str = msg.get("ts", "")
            if not msg_ts_str:
                continue

            try:
                msg_ts = float(msg_ts_str)
            except (ValueError, TypeError):
                logger.warning("Invalid timestamp in message: %s", msg_ts_str)
                continue

            # Skip if we've already processed this message
            if msg_ts <= last_ts:
                continue

            # Process the message
            message_text = msg.get("text", "")
            message_user = msg.get("user", "unknown")

            _process_message(client, channel_id, message_text, msg_ts_str, message_user)

            # Update newest timestamp
            newest_ts = max(newest_ts, msg_ts)

        # Update last processed timestamp
        if newest_ts > last_ts:
            _last_processed_ts[channel_id] = newest_ts
            logger.debug(
                "Updated last processed timestamp for channel %s to %s",
                channel_id,
                newest_ts,
            )

    except SlackApiError as exc:
        error_msg = (
            exc.response.get("error", "unknown error")
            if hasattr(exc, "response")
            else str(exc)
        )
        logger.exception("Error polling channel %s: %s", channel_id, error_msg)
    except Exception as e:
        logger.exception("Unexpected error polling channel %s", channel_id)


async def _polling_loop() -> None:
    """Run the main polling loop every 30 seconds."""
    global _polling_active

    logger.info("Starting message polling loop")
    _polling_active = True

    while _polling_active:
        try:
            # Get monitored channels
            channels = _get_monitored_channels()
            if not channels:
                logger.debug("No channels to monitor, sleeping...")
                await asyncio.sleep(30)
                continue

            # Get bot token from store
            # For now, we'll use a specific user's bot token from environment variable
            # In a multi-user scenario, we might need to track which user's token to use
            bot_token: str | None = None
            bot_user_id: str | None = None

            # Try to find a bot token using environment variable
            # In production, you might want to store which user's bot token to use
            test_user_id = os.environ.get("POLLING_USER_ID")
            if test_user_id:
                bot_token = get_bot_token(test_user_id)
                if bot_token:
                    bot_user_id = test_user_id

            # If no specific user ID, we can't proceed
            # This is a simplified approach - in production you'd want better token management
            if not bot_token:
                # We can't easily enumerate all users, so we'll log a warning
                logger.warning(
                    "No bot token found. Set POLLING_USER_ID environment variable "
                    "or ensure a user has authenticated via OAuth."
                )
                await asyncio.sleep(30)
                continue

            logger.debug(
                "Polling %d channels with bot token for user %s",
                len(channels),
                bot_user_id,
            )

            # Poll each channel
            for channel_id in channels:
                await _poll_channel(channel_id, bot_token)

        except Exception:
            logger.exception("Error in polling loop")

        # Sleep for 30 seconds before next poll
        await asyncio.sleep(30)

    logger.info("Message polling loop stopped")


def start_polling() -> None:
    """Start the background polling task."""
    global _polling_task

    if _polling_task is not None and not _polling_task.done():
        logger.warning("Polling task already running")
        return

    logger.info("Starting message polling service")
    try:
        # Get or create event loop
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # If no event loop exists, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    _polling_task = loop.create_task(_polling_loop())


def stop_polling() -> None:
    """Stop the background polling task."""
    global _polling_active, _polling_task

    logger.info("Stopping message polling service")
    _polling_active = False

    if _polling_task and not _polling_task.done():
        _polling_task.cancel()
        _polling_task = None
