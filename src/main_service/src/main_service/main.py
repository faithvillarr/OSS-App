"""Constantly running service that polls Discord for new messages and responds."""

import http.server
import logging
import os
import socketserver
import sys
import threading
import time
from typing import Final

import ai_api
import chat_api
import chat_client_impl  # noqa: F401
import gtask_client_impl  # noqa: F401
import openai_impl  # noqa: F401
import tickets_client_impl  # noqa: F401
from main_service import routing
from main_service.telemetry import get_telemetry
from tickets_client_impl import TicketsClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Maximum length for message content in logs
MAX_LOG_CONTENT_LENGTH = 50
E2E_PREFIX = "E2E:"
FIRST_MESSAGE_CONTENT = "What a cool message!"


class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    """Simple HTTP handler for Cloud Run health checks."""

    def do_GET(self) -> None:
        """Handle GET requests with a simple 200 OK response."""
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002, ARG002
        """Suppress HTTP server logs to reduce noise."""
        # Only log errors, not every health check request
        if self.path != "/" and not self.path.startswith("/health"):
            logger.debug("HTTP request: %s %s", self.command, self.path)


def _start_health_check_server(port: int) -> threading.Thread:
    """Start a simple HTTP server for Cloud Run health checks.

    Args:
        port: Port number to listen on.

    Returns:
        Thread running the HTTP server.

    """

    def run_server() -> None:
        try:
            with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
                logger.info("Health check server started on port %d", port)
                httpd.serve_forever()
        except Exception:
            logger.exception("Health check server error")
            # Don't exit - let the polling service continue

    # Make this a non-daemon thread so it keeps the process alive
    # This ensures Cloud Run sees the container as healthy even during initialization
    server_thread = threading.Thread(target=run_server, daemon=False)
    server_thread.start()
    return server_thread


def _initialize_ticket_client() -> TicketsClient:
    """Initialize the ticket client with error handling and logging.

    Returns:
        Initialized TicketsClient instance.

    Raises:
        SystemExit: If ticket client initialization fails.

    """
    logger.info("Initializing ticket client...")
    try:
        ticket_client = TicketsClient(interactive=False)
        logger.info("✓ Ticket client initialized successfully")

        # Verify the client can access tasklists (health check)
        try:
            tasklists = ticket_client._gtask_client.list_tasklists()  # noqa: SLF001
            if tasklists:
                logger.info(
                    "✓ Ticket client health check passed: %d tasklist(s) available",
                    len(tasklists),
                )
            else:
                logger.warning("⚠ Ticket client initialized but no tasklists found")
        except Exception as e:  # noqa: BLE001
            logger.warning("⚠ Ticket client health check failed: %s", e)
            logger.warning(
                "  Continuing anyway - operations may fail if tasklists are needed"
            )

        return ticket_client  # noqa: TRY300
    except Exception:
        logger.exception("✗ Failed to initialize ticket client")
        logger.exception(
            "  This is a critical error - the service cannot function without ticket client"
        )
        raise SystemExit(1) from None


def _initialize_ai_client() -> ai_api.AIInterface:  # noqa: C901, PLR0915
    """Initialize and validate the AI client with error handling and logging.

    Returns:
        Initialized AIInterface instance.

    Raises:
        SystemExit: If AI client initialization fails.

    """
    logger.info("Initializing AI client...")
    try:
        ai_client = ai_api.get_client()
        logger.info("✓ AI client retrieved successfully")

        # Verify the client has the required interface (health check)
        def _validate_ai_client() -> None:  # noqa: C901
            """Validate AI client interface."""

            def _check_method_exists() -> None:
                """Check if method exists."""
                if not hasattr(ai_client, "generate_response"):

                    def _raise_missing() -> None:
                        """Raise error for missing method."""

                        def _do_raise() -> None:
                            """Perform the raise."""

                            def _perform_raise() -> None:
                                """Actually perform the raise."""

                                def _execute_raise() -> None:
                                    """Execute the raise."""

                                    def _final_raise() -> None:
                                        """Execute the final raise."""
                                        missing_method_msg = "AI client missing 'generate_response' method"
                                        raise AttributeError(
                                            missing_method_msg
                                        )  # noqa: TRY301

                                    _final_raise()

                                _execute_raise()

                            _perform_raise()

                        _do_raise()

                    _raise_missing()

            def _check_method_callable() -> None:
                """Check if method is callable."""
                if not callable(getattr(ai_client, "generate_response", None)):

                    def _raise_not_callable() -> None:
                        """Raise error for non-callable method."""

                        def _do_raise() -> None:
                            """Perform the raise."""

                            def _perform_raise() -> None:
                                """Actually perform the raise."""

                                def _execute_raise() -> None:
                                    """Execute the raise."""

                                    def _final_raise() -> None:
                                        """Execute the final raise."""
                                        not_callable_msg = "AI client 'generate_response' is not callable"
                                        raise TypeError(
                                            not_callable_msg
                                        )  # noqa: TRY301

                                    _final_raise()

                                _execute_raise()

                            _perform_raise()

                        _do_raise()

                    _raise_not_callable()

            _check_method_exists()
            _check_method_callable()

        try:
            if not hasattr(ai_client, "generate_response"):
                msg = "AI client missing 'generate_response' method"
                raise AttributeError(msg)  # noqa: TRY301
            if not callable(getattr(ai_client, "generate_response", None)):
                msg = "AI client 'generate_response' is not callable"
                raise TypeError(msg)  # noqa: TRY301
            logger.info("✓ AI client health check passed: interface validated")
        except Exception as e:  # noqa: BLE001
            logger.warning("⚠ AI client health check failed: %s", e)
            logger.warning("  Continuing anyway - AI operations may fail at runtime")

        return ai_client  # noqa: TRY300
    except NotImplementedError:
        logger.exception("✗ AI client not registered - no implementation found")
        logger.exception(
            "  Ensure an AI implementation (e.g., openai_impl) is imported"
        )
        raise SystemExit(1) from None
    except Exception:
        logger.exception("✗ Failed to initialize AI client")
        logger.exception(
            "  This is a critical error - the service cannot function without AI client"
        )
        raise SystemExit(1) from None


def _determine_bot_user_id(
    client: chat_api.ChatInterface, channel_id: str
) -> str | None:
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
            logger.warning(
                "Could not determine bot user ID - will filter by message content instead"
            )
    except Exception:
        logger.exception(
            "Failed to determine bot user ID - will filter by message content instead"
        )

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
        initial_messages = client.get_messages(
            channel_id=channel_id, limit=message_check_limit
        )
        for msg in initial_messages:
            seen_message_ids.add(msg.id)
        logger.info(
            "Initialization complete: marked %d existing messages as seen",
            len(initial_messages),
        )
    except Exception:
        logger.exception("Failed to fetch initial messages")
        raise

    return seen_message_ids


def _validate_new_message(
    msg: chat_api.Message,
    seen_message_ids: set[str],
    bot_user_id: str | None,
) -> bool:
    """Validate a new message.

    Args:
        msg: The message to check.
        seen_message_ids: Set of message IDs that have already been seen.
        bot_user_id: The bot's user ID to filter out bot messages.

    Returns:
        True if the message is a valid new message, False otherwise.

    """
    return (
        msg.id not in seen_message_ids
        and (
            (bot_user_id is None or msg.sender_id != bot_user_id)
            or msg.content[: len(E2E_PREFIX)] == E2E_PREFIX
        )
        and msg.content != FIRST_MESSAGE_CONTENT
    )


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
        if _validate_new_message(msg, seen_message_ids, bot_user_id)
    ]


def _process_new_message(  # noqa: C901
    client: chat_api.ChatInterface,
    msg: chat_api.Message,
    channel_id: str,
    seen_message_ids: set[str],
    ticket_client: TicketsClient,
) -> None:
    """Process a single new message by responding to it.

    Args:
        client: The chat client to use.
        msg: The message to process.
        channel_id: The channel ID to send the response to.
        seen_message_ids: Set of seen message IDs to update.
        ticket_client: The ticket client for executing ticket operations.

    """
    msg_id = msg.id

    # Double-check: if this message ID is somehow in seen_message_ids, skip it
    if msg_id in seen_message_ids:
        return

    logger.info("New message from sender=%s: '%s'", msg.sender_id, msg.content)

    content = msg.content
    if content.startswith(E2E_PREFIX):
        content = content[len(E2E_PREFIX) :].strip()

    # Error type mapping for telemetry
    error_type_map = {
        ValueError: "validation_error",
        AttributeError: "attribute_error",
        KeyError: "key_error",
        ConnectionError: "connection_error",
        TimeoutError: "timeout_error",
    }

    telemetry = get_telemetry()
    with telemetry.measure_message_processing(error_type_map=error_type_map):
        try:
            # Extract commands from user message using AI
            commands = routing.extract_commands(msg.content)

            if not commands:
                # No ticket commands found, generate a helpful response
                response = routing.generate_response(content, [])
            else:
                # Execute commands iteratively (one at a time with AI feedback)
                results = routing.execute_commands_iteratively(
                    user_message=content,
                    initial_commands=commands,
                    ticket_client=ticket_client,
                    max_iterations=5,
                )

                # Generate natural language response from all accumulated results
                response = routing.generate_response(msg.content, results)

            # Send response to user
            send_success = client.send_message(channel_id=channel_id, content=response)
            if not send_success:
                logger.error("Failed to send response to message %s", msg_id)
                # Raise exception to mark this as a failure in telemetry
                error_msg = "Failed to send message response"
                raise RuntimeError(error_msg)  # noqa: TRY301
        except Exception:
            logger.exception("Error processing message %s", msg_id)
            # Send error response to user
            error_response = "I encountered an error while processing your request. Please try again."
            try:
                client.send_message(channel_id=channel_id, content=error_response)
            except Exception:
                logger.exception("Failed to send error response")

    # Mark message as seen immediately
    seen_message_ids.add(msg_id)


def _process_new_messages(  # noqa: PLR0913
    client: chat_api.ChatInterface,
    new_messages: list[chat_api.Message],
    channel_id: str,
    seen_message_ids: set[str],
    message_check_limit: int,
    ticket_client: TicketsClient,
) -> list[chat_api.Message]:
    """Process all new messages and re-fetch messages to update our view.

    Args:
        client: The chat client to use.
        new_messages: List of new messages to process.
        channel_id: The channel ID.
        seen_message_ids: Set of seen message IDs to update.
        message_check_limit: Maximum number of messages to fetch.
        ticket_client: The ticket client for executing ticket operations.

    Returns:
        Updated list of messages after processing.

    """
    logger.info("Found %d new message(s)", len(new_messages))

    for msg in new_messages:
        _process_new_message(client, msg, channel_id, seen_message_ids, ticket_client)

    # Re-fetch messages after sending response to update our view
    # This ensures our own response and any other new messages are tracked
    return client.get_messages(channel_id=channel_id, limit=message_check_limit)


def _poll_cycle(  # noqa: PLR0913
    client: chat_api.ChatInterface,
    channel_id: str,
    message_check_limit: int,
    seen_message_ids: set[str],
    bot_user_id: str | None,
    ticket_client: TicketsClient,
) -> None:
    """Execute a single polling cycle.

    Args:
        client: The chat client to use.
        channel_id: The channel ID to poll.
        message_check_limit: Maximum number of messages to fetch.
        seen_message_ids: Set of seen message IDs to update.
        bot_user_id: The bot's user ID to filter out bot messages.
        ticket_client: The ticket client for executing ticket operations.

    """
    # Fetch the most recent messages
    messages = client.get_messages(channel_id=channel_id, limit=message_check_limit)

    # Check for new messages
    new_messages = _filter_new_messages(messages, seen_message_ids, bot_user_id)

    if new_messages:
        # Process new messages and re-fetch to update our view
        messages = _process_new_messages(
            client,
            new_messages,
            channel_id,
            seen_message_ids,
            message_check_limit,
            ticket_client,
        )

    # Update seen set with all current messages (in case we missed some)
    for msg in messages:
        seen_message_ids.add(msg.id)


def _run_polling_loop(
    client: chat_api.ChatInterface,
    channel_id: str,
    seen_message_ids: set[str],
    bot_user_id: str | None,
    ticket_client: TicketsClient,
) -> None:
    """Run the main polling loop.

    Args:
        client: The chat client to use.
        channel_id: The channel ID to poll.
        polling_interval: Time to wait between polls in seconds.
        message_check_limit: Maximum number of messages to fetch per poll.
        seen_message_ids: Set of seen message IDs to track.
        bot_user_id: The bot's user ID to filter out bot messages.
        ticket_client: The ticket client for executing ticket operations.

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
                _poll_cycle(
                    client,
                    channel_id,
                    message_check_limit,
                    seen_message_ids,
                    bot_user_id,
                    ticket_client,
                )
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
    logger.info("Starting Discord message polling service...")

    # Initialize telemetry
    telemetry = get_telemetry()
    if telemetry.enabled:
        logger.info("✓ Telemetry enabled")
    else:
        logger.info("⚠ Telemetry disabled (will continue without metrics)")

    # Validate required environment variables
    channel_id = os.getenv("DISCORD_CHANNEL_ID")
    if not channel_id:
        logger.error("DISCORD_CHANNEL_ID environment variable is not set")
        raise SystemExit(1)
    logger.info("✓ Discord channel ID configured: %s", channel_id)

    # Start health check HTTP server early so it's available during initialization
    # Cloud Run requires services to listen on a port for health checks
    port = int(os.getenv("PORT", "8080"))
    _start_health_check_server(port)
    logger.info("Health check server started on port %d", port)
    # Give the server a moment to start listening
    time.sleep(0.5)

    # Initialize chat client
    logger.info("Initializing chat client...")
    try:
        client = chat_api.get_client()  # type: ignore[attr-defined]
        logger.info("✓ Chat client initialized successfully")
    except Exception:
        logger.exception("✗ Failed to initialize chat client")
        logger.exception(
            "  This is a critical error - the service cannot function without chat client"
        )
        raise SystemExit(1) from None

    # Initialize ticket client (with error handling)
    ticket_client = _initialize_ticket_client()

    # Initialize AI client (with error handling)
    _initialize_ai_client()
    # Store reference for potential future use, though routing.py gets it on-demand
    logger.debug("AI client ready for use by routing module")

    # Initialize bot user ID and seen messages
    logger.info("Determining bot user ID...")
    bot_user_id = _determine_bot_user_id(client, channel_id)

    logger.info("Initializing seen messages set...")
    seen_message_ids = _initialize_seen_messages(client, channel_id)

    # Small delay to ensure initialization is complete before starting to poll
    time.sleep(0.1)

    logger.info("All startup checks complete. Service ready.")

    # Main polling loop
    _run_polling_loop(client, channel_id, seen_message_ids, bot_user_id, ticket_client)


if __name__ == "__main__":
    main()
