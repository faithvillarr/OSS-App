"""Configuration and fixtures for main_service integration tests.

This module provides reusable fixtures for mocking external services
(Discord, Google Tasks) to enable integration testing without hitting real APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

# Import main_service components
# These imports are done lazily in fixtures to avoid import errors
# The actual classes are imported when needed in test files
from discord_client_impl.discord_impl import DiscordClient
from tickets_client_impl.tickets_impl import TicketsClient

from tickets_api import Ticket, TicketStatus

pytestmark = pytest.mark.integration


@dataclass
class MockDiscordContext:
    """Context for mocked Discord client."""

    mock_client: MagicMock
    channel_id: str
    user_id: str
    message_id: str


@pytest.fixture
def mock_discord_client() -> MagicMock:
    """Create a mock Discord client.

    Returns:
        MagicMock configured as DiscordClient with common methods mocked.

    """
    mock_client = MagicMock(spec=DiscordClient)
    mock_client.send_message.return_value = True
    mock_client.get_messages.return_value = []
    mock_client.get_message.return_value = MagicMock(
        id="1234567890123456789",
        content="Test message",
        channel_id="123456789012345678",
        sender_id="987654321098765432",
    )
    mock_client.delete_message.return_value = True
    mock_client.get_channel.return_value = MagicMock(
        id="123456789012345678",
        name="test-channel",
    )
    return mock_client


@pytest.fixture
def mock_tickets_client() -> MagicMock:
    """Create a mock TicketsClient.

    Returns:
        MagicMock configured as TicketsClient with common methods mocked.

    """
    mock_client = MagicMock(spec=TicketsClient)

    # Configure default return values

    mock_ticket = MagicMock(spec=Ticket)
    mock_ticket.id = "test_ticket_123"
    mock_ticket.title = "Test Ticket"
    mock_ticket.description = "Test Description"
    mock_ticket.status = TicketStatus.OPEN
    mock_ticket.assignee = None

    mock_client.create_ticket.return_value = mock_ticket
    mock_client.get_ticket.return_value = mock_ticket
    mock_client.search_tickets.return_value = [mock_ticket]
    mock_client.update_ticket.return_value = mock_ticket
    mock_client.delete_ticket.return_value = True

    return mock_client




@pytest.fixture
def mock_discord_context() -> MockDiscordContext:
    """Create a mock Discord context with test data.

    Returns:
        MockDiscordContext with Discord IDs and mock client.

    """
    return MockDiscordContext(
        mock_client=MagicMock(spec=DiscordClient),
        channel_id="123456789012345678",  # Discord channel ID format
        user_id="987654321098765432",  # Discord user ID format
        message_id="1234567890123456789",  # Discord message ID format
    )



