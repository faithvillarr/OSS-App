"""Simple end-to-end tests for tickets operations through Discord bot.

Tests real API calls by sending messages to Discord and verifying bot responses.
Messages must be prefixed with "E2E: " to be processed by the bot.
"""

import os
import subprocess
import time

import pytest
from dotenv import load_dotenv

import chat_api
import chat_client_impl  # noqa: F401

# Load environment variables from .env file
load_dotenv()

# Mark all tests in this file as e2e tests
pytestmark = pytest.mark.e2e

# E2E prefix that the bot recognizes
E2E_PREFIX = "E2E:"

# Time to wait for bot to process and respond (in seconds)
BOT_RESPONSE_TIMEOUT = 30


def _get_channel_id() -> str:
    """Get Discord channel ID from environment."""
    channel_id = os.getenv("DISCORD_CHANNEL_ID")
    if not channel_id:
        pytest.skip("DISCORD_CHANNEL_ID environment variable is not set")
    return channel_id


def _send_message_and_wait_for_response(
    client: chat_api.ChatInterface,
    channel_id: str,
    message: str,
    timeout: int = BOT_RESPONSE_TIMEOUT,
) -> str | None:
    """Send a message to Discord and wait for bot response.

    Args:
        client: The chat client to use.
        channel_id: The Discord channel ID.
        message: The message to send (will be prefixed with E2E_PREFIX).
        timeout: Maximum time to wait for response in seconds.

    Returns:
        The bot's response content, or None if no response received.

    """
    # Get existing messages before sending (to track what's new)
    messages_before = {msg.id for msg in client.get_messages(channel_id=channel_id, limit=20)}

    # Send message with E2E prefix
    full_message = f"{E2E_PREFIX}{message}"
    success = client.send_message(channel_id=channel_id, content=full_message)
    assert success, "Failed to send message to Discord"

    # Wait a bit for message to be sent and bot to start processing
    time.sleep(2)

    # Poll for bot response
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Get recent messages
        messages = client.get_messages(channel_id=channel_id, limit=20)

        # Find new messages (not seen before we sent our message)
        for msg in messages:
            # Skip messages that existed before we sent our test message
            if msg.id in messages_before:
                continue

            # Skip our own test message
            if msg.content == full_message:
                continue

            # This is a new message that's not ours - likely the bot's response
            if len(msg.content.strip()) > 0:
                return msg.content

        # Wait a bit before checking again
        time.sleep(2)

    return None


@pytest.mark.local_credentials
def test_get_all_tickets_e2e(main_service: subprocess.Popen[str]) -> None:
    """Test getting all tickets via Discord bot message.

    Sends "E2E: what are my tickets" and verifies bot responds successfully.
    """
    # Skip in CI if credentials are not available
    if os.environ.get("CIRCLECI") == "true":
        required_env_vars = [
            "DISCORD_BOT_TOKEN",
            "DISCORD_CHANNEL_ID",
            "TASKS_CLIENT_ID",
            "TASKS_CLIENT_SECRET",
            "TASKS_REFRESH_TOKEN",
        ]
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        if missing_vars:
            pytest.skip(f"Missing required environment variables: {missing_vars}")

    # Verify service is still running
    if main_service.poll() is not None:
        pytest.fail(f"Main service process died before test! Return code: {main_service.poll()}")

    # Get channel ID
    channel_id = _get_channel_id()

    # Initialize chat client
    client = chat_api.get_client()  # type: ignore[attr-defined]

    # Send message asking for all tickets
    response = _send_message_and_wait_for_response(
        client=client,
        channel_id=channel_id,
        message="what are my tickets",
    )

    # Verify we got a response
    assert response is not None, "Bot did not respond to 'what are my tickets'"
    assert len(response.strip()) > 0, "Bot response was empty"

    # Verify the response indicates some processing happened
    # (doesn't need to be specific, just that something was returned)
    assert isinstance(response, str), "Bot response should be a string"


@pytest.mark.local_credentials
def test_get_open_tickets_e2e(main_service: subprocess.Popen[str]) -> None:
    """Test getting open tickets via Discord bot message.

    Sends "E2E: what are my open tickets" and verifies bot responds successfully.
    """
    # Skip in CI if credentials are not available
    if os.environ.get("CIRCLECI") == "true":
        required_env_vars = [
            "DISCORD_BOT_TOKEN",
            "DISCORD_CHANNEL_ID",
            "TASKS_CLIENT_ID",
            "TASKS_CLIENT_SECRET",
            "TASKS_REFRESH_TOKEN",
        ]
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        if missing_vars:
            pytest.skip(f"Missing required environment variables: {missing_vars}")

    # Verify service is still running
    if main_service.poll() is not None:
        pytest.fail(f"Main service process died before test! Return code: {main_service.poll()}")

    # Get channel ID
    channel_id = _get_channel_id()

    # Initialize chat client
    client = chat_api.get_client()  # type: ignore[attr-defined]

    # Send message asking for open tickets
    response = _send_message_and_wait_for_response(
        client=client,
        channel_id=channel_id,
        message="what are my open tickets",
    )

    # Verify we got a response
    assert response is not None, "Bot did not respond to 'what are my open tickets'"
    assert len(response.strip()) > 0, "Bot response was empty"

    # Verify the response indicates some processing happened
    # (doesn't need to be specific, just that something was returned)
    assert isinstance(response, str), "Bot response should be a string"
