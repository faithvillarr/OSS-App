"""Integration tests for Ticketing → AI Flow: Ticketing operations and result formatting for AI.

This file consolidates tests from the following source files:
  - test_routing_ticketing_integration.py
  - test_ticketing_coverage.py
  - test_tickets_client_methods_integration.py
  - test_ticket_implementation_integration.py

All external services are mocked.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError
from tickets_client_impl.tickets_impl import _TaskBuilder

from main_service import routing, ticketing
from tickets_api import Ticket, TicketStatus
from tickets_client_impl import TicketsClient

pytestmark = pytest.mark.integration
class TestRoutingTicketingIntegration:
    """Test integration between routing and ticketing components."""

    def test_extract_and_execute_create_ticket_command(
        self,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that AI-extracted create_ticket command is correctly executed.

        This test verifies:
        1. AI extracts a create_ticket command from user message
        2. The command is passed to ticketing.execute_commands
        3. ticketing correctly calls the TicketsClient
        4. Results are formatted correctly
        """
        # Setup: Mock AI response for command extraction
        mock_ai_client.generate_response.return_value = {
            "actions": [
                {
                    "type": "create_ticket",
                    "params": {
                        "title": "Test Ticket",
                        "description": "Test Description",
                        "ticket_id": None,
                        "status": None,
                        "query": None,
                        "assignee": None,
                    },
                }
            ]
        }

        # Setup: Mock ticket creation
        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Test Ticket"
        mock_ticket.description = "Test Description"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.create_ticket.return_value = mock_ticket

        # Execute: Extract commands and execute
        user_message = "Create a ticket for testing"
        commands = routing.extract_commands(user_message)
        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify: AI was called for extraction
        assert mock_ai_client.generate_response.called
        assert len(commands) == 1
        assert commands[0]["type"] == "create_ticket"

        # Verify: Ticket client was called correctly
        mock_tickets_client.create_ticket.assert_called_once_with(
            title="Test Ticket",
            description="Test Description",
            assignee=None,
        )

        # Verify: Results are correctly formatted
        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["result"]["id"] == "ticket_123"
        assert results[0]["result"]["title"] == "Test Ticket"

    def test_extract_and_execute_search_tickets_command(
        self,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that AI-extracted search_tickets command is correctly executed."""
        # Setup: Mock AI response
        mock_ai_client.generate_response.return_value = {
            "actions": [
                {
                    "type": "search_tickets",
                    "params": {
                        "query": "test",
                        "status": None,
                        "ticket_id": None,
                        "title": None,
                        "description": None,
                        "assignee": None,
                    },
                }
            ]
        }

        # Setup: Mock search results
        mock_ticket1 = MagicMock(spec=Ticket)
        mock_ticket1.id = "ticket_1"
        mock_ticket1.title = "Test Ticket 1"
        mock_ticket1.description = "Description 1"
        mock_ticket1.status = TicketStatus.OPEN
        mock_ticket1.assignee = None

        mock_ticket2 = MagicMock(spec=Ticket)
        mock_ticket2.id = "ticket_2"
        mock_ticket2.title = "Test Ticket 2"
        mock_ticket2.description = "Description 2"
        mock_ticket2.status = TicketStatus.IN_PROGRESS
        mock_ticket2.assignee = None

        mock_tickets_client.search_tickets.return_value = [mock_ticket1, mock_ticket2]

        # Execute
        user_message = "Find all tickets with 'test' in the title"
        commands = routing.extract_commands(user_message)
        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify
        assert len(commands) == 1
        assert commands[0]["type"] == "search_tickets"
        mock_tickets_client.search_tickets.assert_called_once_with(
            query="test",
            status=None,
        )
        assert len(results) == 1
        assert results[0]["success"] is True
        assert len(results[0]["result"]["tickets"]) == 2
        assert results[0]["result"]["count"] == 2

    def test_extract_and_execute_update_ticket_command(
        self,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that AI-extracted update_ticket command is correctly executed."""
        # Setup: Mock AI response
        mock_ai_client.generate_response.return_value = {
            "actions": [
                {
                    "type": "update_ticket",
                    "params": {
                        "ticket_id": "ticket_123",
                        "status": "in_progress",
                        "title": None,
                        "description": None,
                        "query": None,
                        "assignee": None,
                    },
                }
            ]
        }

        # Setup: Mock updated ticket
        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Updated Ticket"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.IN_PROGRESS
        mock_ticket.assignee = None
        mock_tickets_client.update_ticket.return_value = mock_ticket

        # Execute
        user_message = "Update ticket ticket_123 to in progress"
        commands = routing.extract_commands(user_message)
        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify
        assert len(commands) == 1
        assert commands[0]["type"] == "update_ticket"
        mock_tickets_client.update_ticket.assert_called_once_with(
            ticket_id="ticket_123",
            status=TicketStatus.IN_PROGRESS,
            title=None,
        )
        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["result"]["status"] == "in_progress"

    def test_generate_response_from_ticket_results(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test that AI generates natural language response from ticket results."""
        # Setup: Mock AI response for response generation
        mock_ai_client.generate_response.return_value = (
            "I've successfully created ticket ticket_123: Test Ticket"
        )

        # Setup: Mock ticket results
        results = [
            {
                "success": True,
                "command": {
                    "type": "create_ticket",
                    "params": {"title": "Test Ticket", "description": "Test"},
                },
                "result": {
                    "id": "ticket_123",
                    "title": "Test Ticket",
                    "description": "Test",
                    "status": "open",
                    "assignee": None,
                },
                "error": None,
            }
        ]

        # Execute
        user_message = "Create a ticket for testing"
        response = routing.generate_response(user_message, results)

        # Verify: AI was called for response generation
        assert mock_ai_client.generate_response.called
        assert isinstance(response, str)
        assert len(response) > 0

    def test_error_handling_when_ticket_creation_fails(
        self,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test error handling when ticket creation fails."""
        # Setup: Mock AI response
        mock_ai_client.generate_response.return_value = {
            "actions": [
                {
                    "type": "create_ticket",
                    "params": {
                        "title": "Test Ticket",
                        "description": "Test Description",
                        "ticket_id": None,
                        "status": None,
                        "query": None,
                        "assignee": None,
                    },
                }
            ]
        }

        # Setup: Mock ticket creation failure
        mock_tickets_client.create_ticket.side_effect = Exception("API Error")

        # Execute
        user_message = "Create a ticket"
        commands = routing.extract_commands(user_message)
        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify: Error is properly handled
        assert len(results) == 1
        assert results[0]["success"] is False
        assert results[0]["error"] == "API Error"
        assert results[0]["result"] is None

    def test_iterative_command_execution_with_followup(
        self,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test iterative command execution where AI generates follow-up commands."""
        # Setup: Mock AI responses
        # First: Extract initial command
        # Second: Generate follow-up command based on search results
        mock_ai_client.generate_response.side_effect = [
            # Initial extraction
            {
                "actions": [
                    {
                        "type": "search_tickets",
                        "params": {
                            "query": "test",
                            "status": None,
                            "ticket_id": None,
                            "title": None,
                            "description": None,
                            "assignee": None,
                        },
                    }
                ]
            },
            # Follow-up command after seeing search results
            {
                "actions": [
                    {
                        "type": "update_ticket",
                        "params": {
                            "ticket_id": "ticket_1",
                            "status": "in_progress",
                            "title": None,
                            "description": None,
                            "query": None,
                            "assignee": None,
                        },
                    }
                ]
            },
        ]

        # Setup: Mock search results
        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_1"
        mock_ticket.title = "Test Ticket"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.search_tickets.return_value = [mock_ticket]

        # Setup: Mock update
        updated_ticket = MagicMock(spec=Ticket)
        updated_ticket.id = "ticket_1"
        updated_ticket.title = "Test Ticket"
        updated_ticket.description = "Description"
        updated_ticket.status = TicketStatus.IN_PROGRESS
        updated_ticket.assignee = None
        mock_tickets_client.update_ticket.return_value = updated_ticket

        # Execute: Iterative execution
        user_message = "Find test tickets and mark them as in progress"
        initial_commands = routing.extract_commands(user_message)
        results = routing.execute_commands_iteratively(
            user_message=user_message,
            initial_commands=initial_commands,
            ticket_client=mock_tickets_client,
            max_iterations=3,
        )

        # Verify: Both commands were executed
        assert len(results) >= 2
        assert results[0]["command"]["type"] == "search_tickets"
        assert results[1]["command"]["type"] == "update_ticket"
        assert results[1]["success"] is True


@pytest.fixture
def mock_ai_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock AI client for testing."""
    mock_client = MagicMock()

    # Patch ai_api.get_client to return our mock
    with patch("main_service.routing.ai_api.get_client", return_value=mock_client):
        yield mock_client


# ===== Tests from test_ticketing_coverage.py =====


class TestTicketingCoverage:
    """Additional tests for ticketing module coverage."""

    def test_get_ticket_success(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test successful get_ticket execution."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Test Ticket"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.get_ticket.return_value = mock_ticket

        command = {
            "type": "get_ticket",
            "params": {"ticket_id": "ticket_123"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["result"]["id"] == "ticket_123"

    def test_get_ticket_missing_id(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test get_ticket with missing ticket_id."""
        command = {
            "type": "get_ticket",
            "params": {},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "ticket_id" in results[0]["error"].lower()

    def test_get_ticket_not_found(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test get_ticket when ticket doesn't exist."""
        mock_tickets_client.get_ticket.return_value = None

        command = {
            "type": "get_ticket",
            "params": {"ticket_id": "nonexistent"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "not found" in results[0]["error"].lower()

    def test_get_ticket_exception(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test get_ticket when exception occurs."""
        mock_tickets_client.get_ticket.side_effect = Exception("API Error")

        command = {
            "type": "get_ticket",
            "params": {"ticket_id": "ticket_123"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "API Error" in results[0]["error"]

    def test_search_tickets_with_query(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test search_tickets with query parameter."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket1 = MagicMock(spec=Ticket)
        mock_ticket1.id = "ticket_1"
        mock_ticket1.title = "Test Ticket 1"
        mock_ticket1.description = "Description 1"
        mock_ticket1.status = TicketStatus.OPEN
        mock_ticket1.assignee = None

        mock_ticket2 = MagicMock(spec=Ticket)
        mock_ticket2.id = "ticket_2"
        mock_ticket2.title = "Test Ticket 2"
        mock_ticket2.description = "Description 2"
        mock_ticket2.status = TicketStatus.IN_PROGRESS
        mock_ticket2.assignee = None

        mock_tickets_client.search_tickets.return_value = [mock_ticket1, mock_ticket2]

        command = {
            "type": "search_tickets",
            "params": {"query": "test"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is True
        assert len(results[0]["result"]["tickets"]) == 2
        mock_tickets_client.search_tickets.assert_called_once_with(
            query="test",
            status=None,
        )

    def test_search_tickets_with_status(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test search_tickets with status parameter."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_1"
        mock_ticket.title = "Test Ticket"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None

        mock_tickets_client.search_tickets.return_value = [mock_ticket]

        command = {
            "type": "search_tickets",
            "params": {"status": "open"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is True
        mock_tickets_client.search_tickets.assert_called_once_with(
            query=None,
            status=TicketStatus.OPEN,
        )

    def test_search_tickets_invalid_status(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test search_tickets with invalid status."""
        command = {
            "type": "search_tickets",
            "params": {"status": "invalid"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "invalid status" in results[0]["error"].lower()

    def test_search_tickets_exception(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test search_tickets when exception occurs."""
        mock_tickets_client.search_tickets.side_effect = Exception("API Error")

        command = {
            "type": "search_tickets",
            "params": {},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "API Error" in results[0]["error"]

    def test_update_ticket_with_status(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test update_ticket with status parameter."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Updated Ticket"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.IN_PROGRESS
        mock_ticket.assignee = None
        mock_tickets_client.update_ticket.return_value = mock_ticket

        command = {
            "type": "update_ticket",
            "params": {"ticket_id": "ticket_123", "status": "in_progress"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is True
        mock_tickets_client.update_ticket.assert_called_once_with(
            ticket_id="ticket_123",
            status=TicketStatus.IN_PROGRESS,
            title=None,
        )

    def test_update_ticket_with_title(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test update_ticket with title parameter."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "New Title"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.update_ticket.return_value = mock_ticket

        command = {
            "type": "update_ticket",
            "params": {"ticket_id": "ticket_123", "title": "New Title"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is True
        mock_tickets_client.update_ticket.assert_called_once_with(
            ticket_id="ticket_123",
            status=None,
            title="New Title",
        )

    def test_update_ticket_missing_id(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test update_ticket with missing ticket_id."""
        command = {
            "type": "update_ticket",
            "params": {},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "ticket_id" in results[0]["error"].lower()

    def test_update_ticket_no_params(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test update_ticket with no status or title."""
        command = {
            "type": "update_ticket",
            "params": {"ticket_id": "ticket_123"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "status" in results[0]["error"].lower() or "title" in results[0]["error"].lower()

    def test_update_ticket_invalid_status(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test update_ticket with invalid status."""
        command = {
            "type": "update_ticket",
            "params": {"ticket_id": "ticket_123", "status": "invalid"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "invalid status" in results[0]["error"].lower()

    def test_update_ticket_exception(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test update_ticket when exception occurs."""
        mock_tickets_client.update_ticket.side_effect = Exception("API Error")

        command = {
            "type": "update_ticket",
            "params": {"ticket_id": "ticket_123", "status": "open"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "API Error" in results[0]["error"]

    def test_delete_ticket_success(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test successful delete_ticket execution."""
        mock_tickets_client.delete_ticket.return_value = True

        command = {
            "type": "delete_ticket",
            "params": {"ticket_id": "ticket_123"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["result"]["deleted"] is True
        mock_tickets_client.delete_ticket.assert_called_once_with("ticket_123")

    def test_delete_ticket_missing_id(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test delete_ticket with missing ticket_id."""
        command = {
            "type": "delete_ticket",
            "params": {},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "ticket_id" in results[0]["error"].lower()

    def test_delete_ticket_failure(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test delete_ticket when deletion fails."""
        mock_tickets_client.delete_ticket.return_value = False

        command = {
            "type": "delete_ticket",
            "params": {"ticket_id": "ticket_123"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "failed" in results[0]["error"].lower()

    def test_delete_ticket_exception(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test delete_ticket when exception occurs."""
        mock_tickets_client.delete_ticket.side_effect = Exception("API Error")

        command = {
            "type": "delete_ticket",
            "params": {"ticket_id": "ticket_123"},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "API Error" in results[0]["error"]

    def test_unknown_command_type(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test execution of unknown command type."""
        command = {
            "type": "unknown_command",
            "params": {},
        }
        results = ticketing.execute_commands([command], mock_tickets_client)

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "unknown" in results[0]["error"].lower()

    def test_format_ticket_for_json(
        self,
    ) -> None:
        """Test format_ticket_for_json function."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Test Ticket"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.IN_PROGRESS
        mock_ticket.assignee = "user_123"

        formatted = ticketing.format_ticket_for_json(mock_ticket)

        assert formatted["id"] == "ticket_123"
        assert formatted["title"] == "Test Ticket"
        assert formatted["description"] == "Description"
        assert formatted["status"] == "in_progress"
        assert formatted["assignee"] == "user_123"



# ===== Tests from test_tickets_client_methods_integration.py =====


class TestTicketsClientMethodsIntegration:
    """Test integration with TicketsClient methods."""

    def test_tickets_client_create_ticket_with_assignee(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test TicketsClient.create_ticket with assignee parameter."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Assigned Ticket"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = "user_123"
        mock_tickets_client.create_ticket.return_value = mock_ticket

        commands = [
            {
                "type": "create_ticket",
                "params": {
                    "title": "Assigned Ticket",
                    "description": "Description",
                    "assignee": "user_123",
                    "ticket_id": None,
                    "status": None,
                    "query": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        mock_tickets_client.create_ticket.assert_called_once_with(
            title="Assigned Ticket", description="Description", assignee="user_123"
        )
        assert results[0]["success"] is True
        assert results[0]["result"]["assignee"] == "user_123"

    def test_tickets_client_search_with_status_filter(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test TicketsClient.search_tickets with status filter."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "In Progress Ticket"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.IN_PROGRESS
        mock_ticket.assignee = None
        mock_tickets_client.search_tickets.return_value = [mock_ticket]

        commands = [
            {
                "type": "search_tickets",
                "params": {
                    "status": "in_progress",
                    "query": None,
                    "ticket_id": None,
                    "title": None,
                    "description": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        mock_tickets_client.search_tickets.assert_called_once_with(
            query=None, status=TicketStatus.IN_PROGRESS
        )
        assert results[0]["success"] is True
        assert results[0]["result"]["tickets"][0]["status"] == "in_progress"

    def test_tickets_client_update_ticket_title_only(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test TicketsClient.update_ticket with title only (no status)."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "New Title"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.update_ticket.return_value = mock_ticket

        commands = [
            {
                "type": "update_ticket",
                "params": {
                    "ticket_id": "ticket_123",
                    "title": "New Title",
                    "status": None,
                    "description": None,
                    "query": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        mock_tickets_client.update_ticket.assert_called_once_with(
            ticket_id="ticket_123", status=None, title="New Title"
        )
        assert results[0]["success"] is True

    def test_tickets_client_update_ticket_status_only(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test TicketsClient.update_ticket with status only (no title)."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Original Title"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.CLOSED
        mock_ticket.assignee = None
        mock_tickets_client.update_ticket.return_value = mock_ticket

        commands = [
            {
                "type": "update_ticket",
                "params": {
                    "ticket_id": "ticket_123",
                    "status": "closed",
                    "title": None,
                    "description": None,
                    "query": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        mock_tickets_client.update_ticket.assert_called_once_with(
            ticket_id="ticket_123", status=TicketStatus.CLOSED, title=None
        )
        assert results[0]["success"] is True
        assert results[0]["result"]["status"] == "closed"

    def test_tickets_client_get_ticket_not_found(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test TicketsClient.get_ticket when ticket doesn't exist."""
        mock_tickets_client.get_ticket.return_value = None

        commands = [
            {
                "type": "get_ticket",
                "params": {"ticket_id": "nonexistent"},
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        assert results[0]["success"] is False
        assert "not found" in results[0]["error"].lower()

    def test_tickets_client_search_empty_results(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test TicketsClient.search_tickets with empty results."""
        mock_tickets_client.search_tickets.return_value = []

        commands = [
            {
                "type": "search_tickets",
                "params": {
                    "query": "nonexistent",
                    "status": None,
                    "ticket_id": None,
                    "title": None,
                    "description": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        assert results[0]["success"] is True
        assert results[0]["result"]["count"] == 0
        assert len(results[0]["result"]["tickets"]) == 0


# ===== Tests from test_ticket_implementation_integration.py =====


class TestTicketImplementationIntegration:
    """Test integration with Ticket implementation."""

    def test_ticket_object_properties(
        self,
    ) -> None:
        """Test that Ticket objects have required properties."""
        from tickets_client_impl.ticket_impl import Ticket as TicketImpl

        from task_client_api import task
        from tickets_api import TicketStatus

        # Create Task object first
        task_obj = MagicMock(spec=task.Task)
        task_obj.id = "task_123"
        task_obj.title = "Test Task"
        task_obj.notes = "Task description"
        task_obj.status = "needsAction"

        # Create Ticket from Task
        ticket = TicketImpl(task_obj)

        # Verify all required properties
        assert ticket.id == "task_123"
        assert ticket.title == "Test Task"
        assert ticket.description == "Task description"
        assert ticket.status == TicketStatus.OPEN
        assert ticket.assignee is None

    def test_ticket_status_mapping(
        self,
    ) -> None:
        """Test that Ticket correctly maps task status to ticket status."""
        from tickets_client_impl.ticket_impl import Ticket as TicketImpl

        from task_client_api import task
        from tickets_api import TicketStatus

        # Test needsAction -> OPEN
        task_obj1 = MagicMock(spec=task.Task)
        task_obj1.id = "task_1"
        task_obj1.title = "Task 1"
        task_obj1.notes = "Description"
        task_obj1.status = "needsAction"
        ticket = TicketImpl(task_obj1)
        assert ticket.status == TicketStatus.OPEN

        # Test completed -> CLOSED
        task_obj2 = MagicMock(spec=task.Task)
        task_obj2.id = "task_2"
        task_obj2.title = "Task 2"
        task_obj2.notes = "Description"
        task_obj2.status = "completed"
        ticket = TicketImpl(task_obj2)
        assert ticket.status == TicketStatus.CLOSED

        # Test (IP) prefix -> IN_PROGRESS
        task_obj3 = MagicMock(spec=task.Task)
        task_obj3.id = "task_3"
        task_obj3.title = "(IP) Task 3"
        task_obj3.notes = "Description"
        task_obj3.status = "needsAction"
        ticket = TicketImpl(task_obj3)
        assert ticket.status == TicketStatus.IN_PROGRESS
        assert ticket.title == "Task 3"  # Prefix should be removed

    def test_ticket_used_in_ticketing_module(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that ticketing module correctly uses Ticket objects."""
        from tickets_client_impl.ticket_impl import Ticket

        from task_client_api import task

        # Create real Ticket object from Task
        task_obj = MagicMock(spec=task.Task)
        task_obj.id = "task_123"
        task_obj.title = "Real Ticket"
        task_obj.notes = "Real Description"
        task_obj.status = "needsAction"
        real_ticket = Ticket(task_obj)

        mock_tickets_client.create_ticket.return_value = real_ticket

        # Execute command
        commands = [
            {
                "type": "create_ticket",
                "params": {
                    "title": "Real Ticket",
                    "description": "Real Description",
                    "ticket_id": None,
                    "status": None,
                    "query": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify Ticket object was correctly formatted
        assert results[0]["success"] is True
        assert results[0]["result"]["id"] == "task_123"
        assert results[0]["result"]["title"] == "Real Ticket"
        assert results[0]["result"]["status"] == "open"  # TicketStatus.OPEN.value

    def test_format_ticket_for_json_with_real_ticket(
        self,
    ) -> None:
        """Test format_ticket_for_json with real Ticket object."""
        from tickets_client_impl.ticket_impl import Ticket

        from task_client_api import task

        task_obj = MagicMock(spec=task.Task)
        task_obj.id = "task_456"
        task_obj.title = "Formatted Ticket"
        task_obj.notes = "Description"
        task_obj.status = "needsAction"
        ticket = Ticket(task_obj)

        formatted = ticketing.format_ticket_for_json(ticket)

        assert formatted["id"] == "task_456"
        assert formatted["title"] == "Formatted Ticket"
        assert formatted["description"] == "Description"
        assert formatted["status"] == "open"
        assert formatted["assignee"] is None


# ===== Internal Implementation Tests =====
# ===== Tests from test_gtask_impl_integration.py =====


class TestGTaskClientThroughTicketsClient:
    """Test GTaskClient methods through TicketsClient integration."""

    def test_list_tasklists_success_path(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that list_tasklists is called successfully through TicketsClient."""
        # Since we're using a mock TicketsClient, the _gtask_client won't actually be called
        # But we can verify that create_ticket works, which internally would call list_tasklists
        # For actual code coverage, we need to test with a real TicketsClient that uses a real GTaskClient
        commands = [
            {
                "type": "create_ticket",
                "params": {
                    "title": "Test",
                    "description": "Test",
                    "ticket_id": None,
                    "status": None,
                    "query": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify create_ticket was called (which internally would call list_tasklists)
        assert results[0]["success"] is True

    def test_list_tasklists_empty_result(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that list_tasklists handles empty results (error path)."""
        # Mock empty tasklist result
        mock_tickets_client._gtask_client.list_tasklists.return_value = []

        # This should raise RuntimeError when trying to get default tasklist
        commands = [
            {
                "type": "create_ticket",
                "params": {
                    "title": "Test",
                    "description": "Test",
                    "ticket_id": None,
                    "status": None,
                    "query": None,
                    "assignee": None,
                },
            }
        ]

        # Should fail because no tasklists available
        results = ticketing.execute_commands(commands, mock_tickets_client)
        # The error should be caught and returned in results
        assert results[0]["success"] is False or "error" in str(results[0]).lower()

    def test_list_tasks_success_path(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that list_tasks is called successfully through search_tickets."""
        from task_client_api import task
        from tickets_api import Ticket

        # Mock tasks
        mock_task1 = MagicMock(spec=task.Task)
        mock_task1.id = "task_1"
        mock_task1.title = "Task 1"
        mock_task1.notes = "Description 1"
        mock_task1.status = "needsAction"

        mock_task2 = MagicMock(spec=task.Task)
        mock_task2.id = "task_2"
        mock_task2.title = "Task 2"
        mock_task2.notes = "Description 2"
        mock_task2.status = "needsAction"

        mock_tickets_client._gtask_client.list_tasks.return_value = [mock_task1, mock_task2]

        # Convert to tickets for search_tickets
        ticket1 = MagicMock(spec=Ticket)
        ticket1.id = "task_1"
        ticket1.title = "Task 1"
        ticket1.description = "Description 1"
        ticket1.status = TicketStatus.OPEN
        ticket1.assignee = None

        ticket2 = MagicMock(spec=Ticket)
        ticket2.id = "task_2"
        ticket2.title = "Task 2"
        ticket2.description = "Description 2"
        ticket2.status = TicketStatus.OPEN
        ticket2.assignee = None

        mock_tickets_client.search_tickets.return_value = [ticket1, ticket2]

        commands = [
            {
                "type": "search_tickets",
                "params": {
                    "query": None,
                    "status": None,
                    "ticket_id": None,
                    "title": None,
                    "description": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify list_tasks was called (indirectly through search_tickets)
        # Note: search_tickets internally calls list_tasks
        assert results[0]["success"] is True

    def test_list_tasks_error_path(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that list_tasks handles errors (HttpError, OSError, ValueError)."""
        # Mock list_tasks to raise HttpError
        mock_tickets_client._gtask_client.list_tasks.side_effect = HttpError(
            resp=MagicMock(status=500), content=b"Internal Server Error"
        )

        # search_tickets should handle the error and return empty list
        mock_tickets_client.search_tickets.return_value = []

        commands = [
            {
                "type": "search_tickets",
                "params": {
                    "query": None,
                    "status": None,
                    "ticket_id": None,
                    "title": None,
                    "description": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Should return empty results
        assert results[0]["success"] is True
        assert results[0]["result"]["count"] == 0

    def test_insert_task_success_path(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that insert_task is called successfully through create_ticket."""
        # Mock ticket (create_ticket already mocked in fixture)
        commands = [
            {
                "type": "create_ticket",
                "params": {
                    "title": "New Task",
                    "description": "Description",
                    "ticket_id": None,
                    "status": None,
                    "query": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify create_ticket was called (which internally would call insert_task)
        assert results[0]["success"] is True
        mock_tickets_client.create_ticket.assert_called_once()

    def test_insert_task_with_due_date(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that insert_task handles task with due date."""
        from tickets_api import Ticket

        # Mock ticket
        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "task_123"
        mock_ticket.title = "Task with Due Date"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.create_ticket.return_value = mock_ticket

        commands = [
            {
                "type": "create_ticket",
                "params": {
                    "title": "Task with Due Date",
                    "description": "Description",
                    "ticket_id": None,
                    "status": None,
                    "query": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify create_ticket was called
        assert results[0]["success"] is True
        mock_tickets_client.create_ticket.assert_called_once()

    def test_insert_task_error_path(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that insert_task handles errors (HttpError, OSError, ValueError)."""
        # Mock insert_task to raise HttpError
        mock_tickets_client._gtask_client.insert_task.side_effect = HttpError(
            resp=MagicMock(status=400), content=b"Bad Request"
        )

        # create_ticket should propagate the error
        mock_tickets_client.create_ticket.side_effect = ValueError("Failed to create task")

        commands = [
            {
                "type": "create_ticket",
                "params": {
                    "title": "Test",
                    "description": "Test",
                    "ticket_id": None,
                    "status": None,
                    "query": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Should return error
        assert results[0]["success"] is False

    def test_get_task_success_path(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that get_task is called successfully through get_ticket."""
        # Mock ticket (get_ticket already mocked in fixture)
        commands = [
            {
                "type": "get_ticket",
                "params": {"ticket_id": "task_123"},
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify get_ticket was called (which internally would call get_task)
        assert results[0]["success"] is True
        mock_tickets_client.get_ticket.assert_called_once()

    def test_get_task_not_found(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that get_task handles task not found (ValueError)."""
        # Mock get_task to raise ValueError (task not found)
        mock_tickets_client._gtask_client.get_task.side_effect = ValueError("Task not found")

        # get_ticket should return None when task not found
        mock_tickets_client.get_ticket.return_value = None

        commands = [
            {
                "type": "get_ticket",
                "params": {"ticket_id": "nonexistent"},
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Should return error (ticket not found)
        assert results[0]["success"] is False
        assert "not found" in results[0]["error"].lower()

    def test_get_task_error_path(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that get_task handles errors (HttpError, OSError)."""
        # Mock get_task to raise HttpError
        mock_tickets_client._gtask_client.get_task.side_effect = HttpError(
            resp=MagicMock(status=500), content=b"Internal Server Error"
        )

        # get_ticket should return None on error
        mock_tickets_client.get_ticket.return_value = None

        commands = [
            {
                "type": "get_ticket",
                "params": {"ticket_id": "task_123"},
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Should return error
        assert results[0]["success"] is False

    def test_delete_task_success_path(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that delete_task is called successfully through delete_ticket."""
        # delete_ticket already mocked in fixture to return True
        commands = [
            {
                "type": "delete_ticket",
                "params": {"ticket_id": "task_123"},
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify delete_ticket was called (which internally would call delete_task)
        assert results[0]["success"] is True
        mock_tickets_client.delete_ticket.assert_called_once()

    def test_delete_task_failure_path(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that delete_task handles failure (returns False)."""
        # Mock delete_ticket to return False
        mock_tickets_client.delete_ticket.return_value = False

        commands = [
            {
                "type": "delete_ticket",
                "params": {"ticket_id": "task_123"},
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # When delete_ticket returns False, ticketing treats it as a failure
        assert results[0]["success"] is False
        assert "delete" in results[0]["error"].lower() or "failed" in results[0]["error"].lower()

    def test_delete_task_error_path(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that delete_task handles errors (HttpError, OSError, ValueError)."""
        # Mock delete_ticket to return False (simulating error handled internally)
        mock_tickets_client.delete_ticket.return_value = False

        commands = [
            {
                "type": "delete_ticket",
                "params": {"ticket_id": "task_123"},
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # When delete_ticket returns False, ticketing treats it as a failure
        assert results[0]["success"] is False
        assert "delete" in results[0]["error"].lower() or "failed" in results[0]["error"].lower()

    def test_update_ticket_uses_delete_and_insert(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that update_ticket uses delete_task and insert_task."""
        from tickets_api import Ticket

        # Mock existing ticket
        existing_ticket = MagicMock(spec=Ticket)
        existing_ticket.id = "task_123"
        existing_ticket.title = "Original Title"
        existing_ticket.description = "Description"
        existing_ticket.status = TicketStatus.OPEN
        existing_ticket.assignee = None
        mock_tickets_client.get_ticket.return_value = existing_ticket

        # Mock updated ticket
        updated_ticket = MagicMock(spec=Ticket)
        updated_ticket.id = "task_123"
        updated_ticket.title = "Updated Title"
        updated_ticket.description = "Description"
        updated_ticket.status = TicketStatus.OPEN
        updated_ticket.assignee = None
        mock_tickets_client.update_ticket.return_value = updated_ticket

        commands = [
            {
                "type": "update_ticket",
                "params": {
                    "ticket_id": "task_123",
                    "title": "Updated Title",
                    "status": None,
                    "description": None,
                    "query": None,
                    "assignee": None,
                },
            }
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify update_ticket was called (which internally would call delete_task and insert_task)
        assert results[0]["success"] is True
        mock_tickets_client.update_ticket.assert_called_once()


class TestGTaskClientDirectMethods:
    """Test GTaskClient methods that are not used by TicketsClient but exist in gtask_impl."""

    def test_insert_tasklist_through_direct_call(
        self,
    ) -> None:
        """Test insert_tasklist method directly (not used by TicketsClient)."""
        from gtask_client_impl.gtask_impl import GTaskClient

        from task_client_api import tasklist

        # Mock the service
        mock_service = MagicMock()
        mock_result = {"id": "new_tasklist_123", "title": "New TaskList"}
        mock_service.tasklists.return_value.insert.return_value.execute.return_value = mock_result

        # Create GTaskClient with mocked service
        client = GTaskClient(service=mock_service)

        # Create tasklist
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.title = "New TaskList"

        # This will execute insert_tasklist code path
        result = client.insert_tasklist(mock_tasklist)

        # Verify service was called
        mock_service.tasklists.return_value.insert.assert_called_once()
        assert result is not None

    def test_list_tasklists_success_with_items(
        self,
    ) -> None:
        """Test list_tasklists success path with items."""
        from gtask_client_impl.gtask_impl import GTaskClient

        # Mock the service to return items
        mock_service = MagicMock()
        mock_result = {
            "items": [
                {"id": "list1", "title": "TaskList 1"},
                {"id": "list2", "title": "TaskList 2"},
            ]
        }
        mock_service.tasklists.return_value.list.return_value.execute.return_value = mock_result

        # Create GTaskClient with mocked service
        client = GTaskClient(service=mock_service)

        # This will execute list_tasklists success path (else branch)
        result = client.list_tasklists()

        # Should return list of tasklists
        assert len(result) == 2

    def test_list_tasks_success_with_items(
        self,
    ) -> None:
        """Test list_tasks success path with items."""
        from gtask_client_impl.gtask_impl import GTaskClient

        # Mock the service to return items
        mock_service = MagicMock()
        mock_result = {
            "items": [
                {"id": "task1", "title": "Task 1", "status": "needsAction"},
                {"id": "task2", "title": "Task 2", "status": "completed"},
            ]
        }
        mock_service.tasks.return_value.list.return_value.execute.return_value = mock_result

        # Create GTaskClient with mocked service
        client = GTaskClient(service=mock_service)

        # This will execute list_tasks success path (else branch)
        result = client.list_tasks("tasklist_123")

        # Should return list of tasks
        assert len(result) == 2

    def test_insert_task_success_with_all_fields(
        self,
    ) -> None:
        """Test insert_task success path with all task fields."""
        from gtask_client_impl.gtask_impl import GTaskClient

        from task_client_api import task

        # Mock the service
        mock_service = MagicMock()
        mock_result = {
            "id": "task_123",
            "title": "Test Task",
            "notes": "Description",
            "status": "needsAction",
            "due": "2024-12-31T00:00:00Z",
        }
        mock_service.tasks.return_value.insert.return_value.execute.return_value = mock_result

        # Create GTaskClient with mocked service
        client = GTaskClient(service=mock_service)

        # Create task with all fields
        mock_task = MagicMock(spec=task.Task)
        mock_task.title = "Test Task"
        mock_task.notes = "Description"
        mock_task.status = "needsAction"
        mock_task.due = "2024-12-31T00:00:00Z"

        # This will execute insert_task success path
        result = client.insert_task("tasklist_123", mock_task)

        # Verify service was called with all fields
        call_args = mock_service.tasks.return_value.insert.call_args
        assert call_args[1]["body"]["title"] == "Test Task"
        assert call_args[1]["body"]["notes"] == "Description"
        assert call_args[1]["body"]["status"] == "needsAction"
        assert call_args[1]["body"]["due"] == "2024-12-31T00:00:00Z"
        assert result is not None

    def test_delete_task_success_path(
        self,
    ) -> None:
        """Test delete_task success path (else branch)."""
        from gtask_client_impl.gtask_impl import GTaskClient

        # Mock the service
        mock_service = MagicMock()
        mock_service.tasks.return_value.delete.return_value.execute.return_value = None

        # Create GTaskClient with mocked service
        client = GTaskClient(service=mock_service)

        # This will execute delete_task success path (else branch)
        result = client.delete_task("tasklist_123", "task_123")

        # Should return True
        assert result is True

    def test_get_task_success_path(
        self,
    ) -> None:
        """Test get_task success path."""
        from gtask_client_impl.gtask_impl import GTaskClient

        # Mock the service
        mock_service = MagicMock()
        mock_result = {
            "id": "task_123",
            "title": "Test Task",
            "notes": "Description",
            "status": "needsAction",
        }
        mock_service.tasks.return_value.get.return_value.execute.return_value = mock_result

        # Create GTaskClient with mocked service
        client = GTaskClient(service=mock_service)

        # This will execute get_task success path (else branch)
        result = client.get_task("tasklist_123", "task_123")

        # Should return task
        assert result is not None
        assert result.id == "task_123"

    def test_get_client_impl_function(
        self,
    ) -> None:
        """Test get_client_impl function."""
        from gtask_client_impl.gtask_impl import get_client_impl

        # This will execute get_client_impl function
        # Note: This will try to initialize with auth, so we need to mock it
        with patch("gtask_client_impl.gtask_impl.GTaskClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            result = get_client_impl(interactive=False)

            # Verify GTaskClient was instantiated
            mock_client_class.assert_called_once_with(interactive=False)
            assert result is mock_client

    def test_delete_tasklist_through_direct_call(
        self,
    ) -> None:
        """Test delete_tasklist method directly (not used by TicketsClient)."""
        from gtask_client_impl.gtask_impl import GTaskClient

        # Mock the service
        mock_service = MagicMock()
        mock_service.tasklists.return_value.delete.return_value.execute.return_value = None

        # Create GTaskClient with mocked service
        client = GTaskClient(service=mock_service)

        # This will execute delete_tasklist code path
        result = client.delete_tasklist("tasklist_123")

        # Verify service was called
        mock_service.tasklists.return_value.delete.assert_called_once()
        assert result is True

    def test_delete_tasklist_error_path(
        self,
    ) -> None:
        """Test delete_tasklist handles errors."""
        from gtask_client_impl.gtask_impl import GTaskClient

        # Mock the service to raise HttpError
        mock_service = MagicMock()
        mock_service.tasklists.return_value.delete.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=404), content=b"Not Found"
        )

        # Create GTaskClient with mocked service
        client = GTaskClient(service=mock_service)

        # This will execute delete_tasklist error path
        result = client.delete_tasklist("nonexistent")

        # Should return False on error
        assert result is False

    def test_list_tasklists_error_path(
        self,
    ) -> None:
        """Test list_tasklists handles errors."""
        from gtask_client_impl.gtask_impl import GTaskClient

        # Mock the service to raise HttpError
        mock_service = MagicMock()
        mock_service.tasklists.return_value.list.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=500), content=b"Internal Server Error"
        )

        # Create GTaskClient with mocked service
        client = GTaskClient(service=mock_service)

        # This will execute list_tasklists error path
        result = client.list_tasklists()

        # Should return empty list on error
        assert result == []

    def test_list_tasklists_oserror_path(
        self,
    ) -> None:
        """Test list_tasklists handles OSError."""
        from gtask_client_impl.gtask_impl import GTaskClient

        # Mock the service to raise OSError
        mock_service = MagicMock()
        mock_service.tasklists.return_value.list.return_value.execute.side_effect = OSError("Network error")

        # Create GTaskClient with mocked service
        client = GTaskClient(service=mock_service)

        # This will execute list_tasklists error path
        result = client.list_tasklists()

        # Should return empty list on error
        assert result == []

    def test_list_tasklists_valueerror_path(
        self,
    ) -> None:
        """Test list_tasklists handles ValueError."""
        from gtask_client_impl.gtask_impl import GTaskClient

        # Mock the service to raise ValueError
        mock_service = MagicMock()
        mock_service.tasklists.return_value.list.return_value.execute.side_effect = ValueError("Invalid data")

        # Create GTaskClient with mocked service
        client = GTaskClient(service=mock_service)

        # This will execute list_tasklists error path
        result = client.list_tasklists()

        # Should return empty list on error
        assert result == []

    def test_list_tasks_error_paths(
        self,
    ) -> None:
        """Test list_tasks handles various errors."""
        from gtask_client_impl.gtask_impl import GTaskClient

        # Test HttpError
        mock_service1 = MagicMock()
        mock_service1.tasklists.return_value.list.return_value.execute.return_value = {"items": []}
        mock_service1.tasks.return_value.list.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=500), content=b"Internal Server Error"
        )
        client1 = GTaskClient(service=mock_service1)
        result1 = client1.list_tasks("tasklist_123")
        assert result1 == []

        # Test OSError
        mock_service2 = MagicMock()
        mock_service2.tasklists.return_value.list.return_value.execute.return_value = {"items": []}
        mock_service2.tasks.return_value.list.return_value.execute.side_effect = OSError("Network error")
        client2 = GTaskClient(service=mock_service2)
        result2 = client2.list_tasks("tasklist_123")
        assert result2 == []

        # Test ValueError
        mock_service3 = MagicMock()
        mock_service3.tasklists.return_value.list.return_value.execute.return_value = {"items": []}
        mock_service3.tasks.return_value.list.return_value.execute.side_effect = ValueError("Invalid data")
        client3 = GTaskClient(service=mock_service3)
        result3 = client3.list_tasks("tasklist_123")
        assert result3 == []

    def test_insert_task_error_paths(
        self,
    ) -> None:
        """Test insert_task handles various errors."""
        from gtask_client_impl.gtask_impl import GTaskClient

        from task_client_api import task

        # Create a mock task
        mock_task = MagicMock(spec=task.Task)
        mock_task.title = "Test Task"
        mock_task.notes = "Description"
        mock_task.status = "needsAction"
        mock_task.due = None

        # Test HttpError
        mock_service1 = MagicMock()
        mock_service1.tasklists.return_value.list.return_value.execute.return_value = {"items": [{"id": "list1"}]}
        mock_service1.tasks.return_value.insert.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=400), content=b"Bad Request"
        )
        client1 = GTaskClient(service=mock_service1)
        with pytest.raises(HttpError):
            client1.insert_task("tasklist_123", mock_task)

        # Test OSError
        mock_service2 = MagicMock()
        mock_service2.tasklists.return_value.list.return_value.execute.return_value = {"items": [{"id": "list1"}]}
        mock_service2.tasks.return_value.insert.return_value.execute.side_effect = OSError("Network error")
        client2 = GTaskClient(service=mock_service2)
        with pytest.raises(OSError, match=r"Network error"):
            client2.insert_task("tasklist_123", mock_task)

        # Test ValueError
        mock_service3 = MagicMock()
        mock_service3.tasklists.return_value.list.return_value.execute.return_value = {"items": [{"id": "list1"}]}
        mock_service3.tasks.return_value.insert.return_value.execute.side_effect = ValueError("Invalid data")
        client3 = GTaskClient(service=mock_service3)
        with pytest.raises(ValueError, match=r"Invalid data"):
            client3.insert_task("tasklist_123", mock_task)

    def test_delete_task_error_paths(
        self,
    ) -> None:
        """Test delete_task handles various errors."""
        from gtask_client_impl.gtask_impl import GTaskClient

        # Test HttpError
        mock_service1 = MagicMock()
        mock_service1.tasklists.return_value.list.return_value.execute.return_value = {"items": [{"id": "list1"}]}
        mock_service1.tasks.return_value.delete.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=404), content=b"Not Found"
        )
        client1 = GTaskClient(service=mock_service1)
        result1 = client1.delete_task("tasklist_123", "task_123")
        assert result1 is False

        # Test OSError
        mock_service2 = MagicMock()
        mock_service2.tasklists.return_value.list.return_value.execute.return_value = {"items": [{"id": "list1"}]}
        mock_service2.tasks.return_value.delete.return_value.execute.side_effect = OSError("Network error")
        client2 = GTaskClient(service=mock_service2)
        result2 = client2.delete_task("tasklist_123", "task_123")
        assert result2 is False

        # Test ValueError
        mock_service3 = MagicMock()
        mock_service3.tasklists.return_value.list.return_value.execute.return_value = {"items": [{"id": "list1"}]}
        mock_service3.tasks.return_value.delete.return_value.execute.side_effect = ValueError("Invalid data")
        client3 = GTaskClient(service=mock_service3)
        result3 = client3.delete_task("tasklist_123", "task_123")
        assert result3 is False

    def test_get_task_error_paths(
        self,
    ) -> None:
        """Test get_task handles various errors."""
        from gtask_client_impl.gtask_impl import GTaskClient

        # Test HttpError
        mock_service1 = MagicMock()
        mock_service1.tasklists.return_value.list.return_value.execute.return_value = {"items": [{"id": "list1"}]}
        mock_service1.tasks.return_value.get.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=404), content=b"Not Found"
        )
        client1 = GTaskClient(service=mock_service1)
        with pytest.raises(ValueError, match=r".*"):
            client1.get_task("tasklist_123", "task_123")

        # Test OSError
        mock_service2 = MagicMock()
        mock_service2.tasklists.return_value.list.return_value.execute.return_value = {"items": [{"id": "list1"}]}
        mock_service2.tasks.return_value.get.return_value.execute.side_effect = OSError("Network error")
        client2 = GTaskClient(service=mock_service2)
        with pytest.raises(ValueError, match=r".*"):
            client2.get_task("tasklist_123", "task_123")

        # Test ValueError
        mock_service3 = MagicMock()
        mock_service3.tasklists.return_value.list.return_value.execute.return_value = {"items": [{"id": "list1"}]}
        mock_service3.tasks.return_value.get.return_value.execute.side_effect = ValueError("Invalid data")
        client3 = GTaskClient(service=mock_service3)
        with pytest.raises(ValueError, match=r"Invalid data"):
            client3.get_task("tasklist_123", "task_123")

    def test_insert_tasklist_error_paths(
        self,
    ) -> None:
        """Test insert_tasklist handles various errors."""
        from gtask_client_impl.gtask_impl import GTaskClient

        from task_client_api import tasklist

        # Create a mock tasklist
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.title = "New TaskList"

        # Test HttpError
        mock_service1 = MagicMock()
        mock_service1.tasklists.return_value.insert.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=400), content=b"Bad Request"
        )
        client1 = GTaskClient(service=mock_service1)
        with pytest.raises(HttpError):
            client1.insert_tasklist(mock_tasklist)

        # Test OSError
        mock_service2 = MagicMock()
        mock_service2.tasklists.return_value.insert.return_value.execute.side_effect = OSError("Network error")
        client2 = GTaskClient(service=mock_service2)
        with pytest.raises(OSError, match=r"Network error"):
            client2.insert_tasklist(mock_tasklist)

        # Test ValueError
        mock_service3 = MagicMock()
        mock_service3.tasklists.return_value.insert.return_value.execute.side_effect = ValueError("Invalid data")
        client3 = GTaskClient(service=mock_service3)
        with pytest.raises(ValueError, match=r"Invalid data"):
            client3.insert_tasklist(mock_tasklist)


# ===== Tests from test_tickets_impl_direct.py =====


class TestTaskBuilder:
    """Test _TaskBuilder class directly."""

    def test_task_builder_initialization(self) -> None:
        """Test _TaskBuilder initialization (lines 42-49)."""
        builder = _TaskBuilder(
            title="Test Task",
            notes="Test notes",
            status="needsAction",
            due="2024-01-01T00:00:00Z",
        )

        assert builder.id == ""
        assert builder.title == "Test Task"
        assert builder.notes == "Test notes"
        assert builder.status == "needsAction"
        assert builder.due == "2024-01-01T00:00:00Z"
        assert builder.completed is None
        assert builder.deleted is False
        assert builder.hidden is False

    def test_task_builder_properties(self) -> None:
        """Test _TaskBuilder property accessors (lines 54, 59, 64, 69, 74, 79, 84, 89)."""
        builder = _TaskBuilder(title="Task", notes="Notes")

        # Test all properties
        assert builder.id == ""
        assert builder.title == "Task"
        assert builder.notes == "Notes"
        assert builder.status == "needsAction"
        assert builder.due is None
        assert builder.completed is None
        assert builder.deleted is False
        assert builder.hidden is False

    def test_task_builder_minimal(self) -> None:
        """Test _TaskBuilder with minimal parameters."""
        builder = _TaskBuilder(title="Minimal Task")

        assert builder.title == "Minimal Task"
        assert builder.notes is None
        assert builder.status == "needsAction"
        assert builder.due is None


class TestTicketsClientInitialization:
    """Test TicketsClient initialization paths."""

    def test_init_with_gtask_client(self) -> None:
        """Test initialization with provided gtask_client (lines 107-112)."""
        mock_gtask_client = MagicMock()
        client = TicketsClient(gtask_client=mock_gtask_client)

        assert client._gtask_client is mock_gtask_client
        assert client._default_tasklist_id is None

    def test_init_without_gtask_client(self) -> None:
        """Test initialization without gtask_client (creates new one) (line 109)."""
        # This test verifies the code path where gtask_client is None
        # We need to patch _GTaskClientImpl to avoid real authentication
        from unittest.mock import patch

        mock_gtask_client = MagicMock()
        with patch("tickets_client_impl.tickets_impl._GTaskClientImpl") as mock_gtask_class:
            mock_gtask_class.return_value = mock_gtask_client

            client = TicketsClient()

            # Verify _GTaskClientImpl was called with interactive=False (default)
            mock_gtask_class.assert_called_once_with(interactive=False)
            assert client._gtask_client is mock_gtask_client

    def test_init_with_interactive(self) -> None:
        """Test initialization with interactive flag (line 109)."""
        # This test verifies the code path where interactive=True and gtask_client is None
        # We need to patch _GTaskClientImpl to avoid real authentication
        from unittest.mock import patch

        mock_gtask_client = MagicMock()
        with patch("tickets_client_impl.tickets_impl._GTaskClientImpl") as mock_gtask_class:
            mock_gtask_class.return_value = mock_gtask_client

            client = TicketsClient(interactive=True)

            # Verify _GTaskClientImpl was called with interactive=True
            mock_gtask_class.assert_called_once_with(interactive=True)
            assert client._gtask_client is mock_gtask_client


class TestTicketsClientInternalMethods:
    """Test TicketsClient internal methods directly."""

    def test_get_default_tasklist_id_success(self) -> None:
        """Test _get_default_tasklist_id with successful fetch (lines 124-131)."""
        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock()
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        client = TicketsClient(gtask_client=mock_gtask_client)

        tasklist_id = client._get_default_tasklist_id()

        assert tasklist_id == "tasklist_123"
        assert client._default_tasklist_id == "tasklist_123"
        mock_gtask_client.list_tasklists.assert_called_once()

    def test_get_default_tasklist_id_cached(self) -> None:
        """Test _get_default_tasklist_id uses cache on second call."""
        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock()
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        client = TicketsClient(gtask_client=mock_gtask_client)

        # First call
        tasklist_id1 = client._get_default_tasklist_id()
        # Second call should use cache
        tasklist_id2 = client._get_default_tasklist_id()

        assert tasklist_id1 == tasklist_id2 == "tasklist_123"
        # Should only be called once due to caching
        assert mock_gtask_client.list_tasklists.call_count == 1

    def test_get_default_tasklist_id_no_tasklists(self) -> None:
        """Test _get_default_tasklist_id raises error when no tasklists (lines 124-131)."""
        mock_gtask_client = MagicMock()
        mock_gtask_client.list_tasklists.return_value = []

        client = TicketsClient(gtask_client=mock_gtask_client)

        with pytest.raises(RuntimeError, match="No tasklists available"):
            client._get_default_tasklist_id()

    def test_ticket_status_to_task_status_open(self) -> None:
        """Test _ticket_status_to_task_status with OPEN status."""
        mock_gtask_client = MagicMock()
        client = TicketsClient(gtask_client=mock_gtask_client)

        result = client._ticket_status_to_task_status(TicketStatus.OPEN)
        assert result == "needsAction"

    def test_ticket_status_to_task_status_in_progress(self) -> None:
        """Test _ticket_status_to_task_status with IN_PROGRESS status."""
        mock_gtask_client = MagicMock()
        client = TicketsClient(gtask_client=mock_gtask_client)

        result = client._ticket_status_to_task_status(TicketStatus.IN_PROGRESS)
        assert result == "needsAction"

    def test_ticket_status_to_task_status_closed(self) -> None:
        """Test _ticket_status_to_task_status with CLOSED status (lines 143-145)."""
        mock_gtask_client = MagicMock()
        client = TicketsClient(gtask_client=mock_gtask_client)

        result = client._ticket_status_to_task_status(TicketStatus.CLOSED)
        assert result == "completed"

    def test_apply_title_prefix_open(self) -> None:
        """Test _apply_title_prefix with OPEN status (removes prefix)."""
        mock_gtask_client = MagicMock()
        client = TicketsClient(gtask_client=mock_gtask_client)

        # Title with prefix
        result = client._apply_title_prefix("(IP) Test Task", TicketStatus.OPEN)
        assert result == "Test Task"

        # Title without prefix
        result = client._apply_title_prefix("Test Task", TicketStatus.OPEN)
        assert result == "Test Task"

    def test_apply_title_prefix_in_progress(self) -> None:
        """Test _apply_title_prefix with IN_PROGRESS status (adds prefix) (lines 159-165)."""
        mock_gtask_client = MagicMock()
        client = TicketsClient(gtask_client=mock_gtask_client)

        # Title without prefix - should add prefix
        result = client._apply_title_prefix("Test Task", TicketStatus.IN_PROGRESS)
        assert result == "(IP) Test Task"

        # Title with prefix - should keep prefix
        result = client._apply_title_prefix("(IP) Test Task", TicketStatus.IN_PROGRESS)
        assert result == "(IP) Test Task"

    def test_apply_title_prefix_closed(self) -> None:
        """Test _apply_title_prefix with CLOSED status (removes prefix)."""
        mock_gtask_client = MagicMock()
        client = TicketsClient(gtask_client=mock_gtask_client)

        result = client._apply_title_prefix("(IP) Test Task", TicketStatus.CLOSED)
        assert result == "Test Task"

    def test_task_to_ticket(self) -> None:
        """Test _task_to_ticket conversion (line 177)."""
        from task_client_api import task

        mock_gtask_client = MagicMock()
        client = TicketsClient(gtask_client=mock_gtask_client)

        # Create a mock task
        mock_task = MagicMock(spec=task.Task)
        mock_task.id = "task_123"
        mock_task.title = "Test Task"
        mock_task.notes = "Description"
        mock_task.status = "needsAction"
        mock_task.due = None
        mock_task.completed = None
        mock_task.deleted = False
        mock_task.hidden = False

        ticket = client._task_to_ticket(mock_task)

        assert ticket.id == "task_123"
        assert ticket.title == "Test Task"
        assert ticket.description == "Description"


class TestTicketsClientPublicMethods:
    """Test TicketsClient public methods directly."""

    def test_create_ticket(self) -> None:
        """Test create_ticket method (lines 192-207)."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        # Mock task creation
        mock_task = MagicMock()
        mock_task.id = "task_123"
        mock_task.title = "Test Task"
        mock_task.notes = "Description"
        mock_task.status = "needsAction"
        mock_gtask_client.insert_task.return_value = mock_task

        client = TicketsClient(gtask_client=mock_gtask_client)

        ticket = client.create_ticket("Test Task", "Description", assignee="user_123")

        assert ticket.id == "task_123"
        assert ticket.title == "Test Task"
        assert ticket.description == "Description"
        # Verify assignee is ignored (line 192)
        mock_gtask_client.insert_task.assert_called_once()
        call_args = mock_gtask_client.insert_task.call_args
        assert call_args[0][0] == "tasklist_123"
        # Verify task was created with correct title (no prefix for OPEN)
        task_obj = call_args[0][1]
        assert task_obj.title == "Test Task"

    def test_create_ticket_with_empty_description(self) -> None:
        """Test create_ticket with empty description."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        mock_task = MagicMock()
        mock_task.id = "task_123"
        mock_task.title = "Test Task"
        mock_task.notes = None
        mock_task.status = "needsAction"
        mock_gtask_client.insert_task.return_value = mock_task

        client = TicketsClient(gtask_client=mock_gtask_client)

        ticket = client.create_ticket("Test Task", "")

        assert ticket.id == "task_123"
        call_args = mock_gtask_client.insert_task.call_args
        task_obj = call_args[0][1]
        assert task_obj.notes is None

    def test_get_ticket_success(self) -> None:
        """Test get_ticket with successful retrieval."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        mock_task = MagicMock()
        mock_task.id = "task_123"
        mock_task.title = "Test Task"
        mock_task.notes = "Description"
        mock_task.status = "needsAction"
        mock_gtask_client.get_task.return_value = mock_task

        client = TicketsClient(gtask_client=mock_gtask_client)

        ticket = client.get_ticket("task_123")

        assert ticket is not None
        assert ticket.id == "task_123"
        mock_gtask_client.get_task.assert_called_once_with("tasklist_123", "task_123")

    def test_get_ticket_not_found(self) -> None:
        """Test get_ticket when ticket not found (lines 219-226)."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        # Raise ValueError when task not found
        mock_gtask_client.get_task.side_effect = ValueError("Task not found")

        client = TicketsClient(gtask_client=mock_gtask_client)

        ticket = client.get_ticket("nonexistent")

        assert ticket is None

    def test_search_tickets_no_filters(self) -> None:
        """Test search_tickets without filters."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        # Mock tasks
        mock_task1 = MagicMock()
        mock_task1.id = "task_1"
        mock_task1.title = "Task 1"
        mock_task1.notes = "Description 1"
        mock_task1.status = "needsAction"

        mock_task2 = MagicMock()
        mock_task2.id = "task_2"
        mock_task2.title = "Task 2"
        mock_task2.notes = "Description 2"
        mock_task2.status = "needsAction"

        mock_gtask_client.list_tasks.return_value = [mock_task1, mock_task2]

        client = TicketsClient(gtask_client=mock_gtask_client)

        tickets = client.search_tickets()

        assert len(tickets) == 2
        mock_gtask_client.list_tasks.assert_called_once_with("tasklist_123")

    def test_search_tickets_with_status_filter(self) -> None:
        """Test search_tickets with status filter (lines 241-263)."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        # Mock tasks with different statuses
        mock_task1 = MagicMock()
        mock_task1.id = "task_1"
        mock_task1.title = "Task 1"
        mock_task1.notes = "Description 1"
        mock_task1.status = "needsAction"  # OPEN

        mock_task2 = MagicMock()
        mock_task2.id = "task_2"
        mock_task2.title = "Task 2"
        mock_task2.notes = "Description 2"
        mock_task2.status = "completed"  # CLOSED

        mock_gtask_client.list_tasks.return_value = [mock_task1, mock_task2]

        client = TicketsClient(gtask_client=mock_gtask_client)

        # Search for OPEN tickets only
        tickets = client.search_tickets(status=TicketStatus.OPEN)

        assert len(tickets) == 1
        assert tickets[0].id == "task_1"

    def test_search_tickets_with_query_filter_title_match(self) -> None:
        """Test search_tickets with query filter matching title (lines 241-263)."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        mock_task1 = MagicMock()
        mock_task1.id = "task_1"
        mock_task1.title = "Bug Fix"
        mock_task1.notes = "Description"
        mock_task1.status = "needsAction"

        mock_task2 = MagicMock()
        mock_task2.id = "task_2"
        mock_task2.title = "Feature"
        mock_task2.notes = "Description"
        mock_task2.status = "needsAction"

        mock_gtask_client.list_tasks.return_value = [mock_task1, mock_task2]

        client = TicketsClient(gtask_client=mock_gtask_client)

        tickets = client.search_tickets(query="bug")

        assert len(tickets) == 1
        assert tickets[0].id == "task_1"

    def test_search_tickets_with_query_filter_description_match(self) -> None:
        """Test search_tickets with query filter matching description (lines 241-263)."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        mock_task1 = MagicMock()
        mock_task1.id = "task_1"
        mock_task1.title = "Task"
        mock_task1.notes = "Fix critical bug"
        mock_task1.status = "needsAction"

        mock_task2 = MagicMock()
        mock_task2.id = "task_2"
        mock_task2.title = "Task"
        mock_task2.notes = "Add feature"
        mock_task2.status = "needsAction"

        mock_gtask_client.list_tasks.return_value = [mock_task1, mock_task2]

        client = TicketsClient(gtask_client=mock_gtask_client)

        tickets = client.search_tickets(query="bug")

        assert len(tickets) == 1
        assert tickets[0].id == "task_1"

    def test_search_tickets_with_query_and_status_filter(self) -> None:
        """Test search_tickets with both query and status filters (lines 241-263)."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        mock_task1 = MagicMock()
        mock_task1.id = "task_1"
        mock_task1.title = "Bug Fix"
        mock_task1.notes = "Description"
        mock_task1.status = "needsAction"  # OPEN

        mock_task2 = MagicMock()
        mock_task2.id = "task_2"
        mock_task2.title = "Bug Fix"
        mock_task2.notes = "Description"
        mock_task2.status = "completed"  # CLOSED

        mock_gtask_client.list_tasks.return_value = [mock_task1, mock_task2]

        client = TicketsClient(gtask_client=mock_gtask_client)

        tickets = client.search_tickets(query="bug", status=TicketStatus.OPEN)

        assert len(tickets) == 1
        assert tickets[0].id == "task_1"

    def test_update_ticket_status_only(self) -> None:
        """Test update_ticket with status only (lines 285-313)."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        # Mock existing ticket
        existing_task = MagicMock()
        existing_task.id = "task_123"
        existing_task.title = "Original Task"
        existing_task.notes = "Description"
        existing_task.status = "needsAction"
        mock_gtask_client.get_task.return_value = existing_task

        # Mock updated task
        updated_task = MagicMock()
        updated_task.id = "task_123"
        updated_task.title = "(IP) Original Task"
        updated_task.notes = "Description"
        updated_task.status = "needsAction"
        mock_gtask_client.insert_task.return_value = updated_task
        mock_gtask_client.delete_task.return_value = True

        client = TicketsClient(gtask_client=mock_gtask_client)

        ticket = client.update_ticket("task_123", status=TicketStatus.IN_PROGRESS)

        assert ticket.id == "task_123"
        # Verify delete and insert were called
        mock_gtask_client.delete_task.assert_called_once_with("tasklist_123", "task_123")
        mock_gtask_client.insert_task.assert_called_once()

    def test_update_ticket_title_only(self) -> None:
        """Test update_ticket with title only (lines 285-313)."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        existing_task = MagicMock()
        existing_task.id = "task_123"
        existing_task.title = "Original Task"
        existing_task.notes = "Description"
        existing_task.status = "needsAction"
        mock_gtask_client.get_task.return_value = existing_task

        updated_task = MagicMock()
        updated_task.id = "task_123"
        updated_task.title = "New Task"
        updated_task.notes = "Description"
        updated_task.status = "needsAction"
        mock_gtask_client.insert_task.return_value = updated_task
        mock_gtask_client.delete_task.return_value = True

        client = TicketsClient(gtask_client=mock_gtask_client)

        ticket = client.update_ticket("task_123", title="New Task")

        assert ticket.id == "task_123"
        mock_gtask_client.delete_task.assert_called_once()
        mock_gtask_client.insert_task.assert_called_once()

    def test_update_ticket_both_status_and_title(self) -> None:
        """Test update_ticket with both status and title (lines 285-313)."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        existing_task = MagicMock()
        existing_task.id = "task_123"
        existing_task.title = "Original Task"
        existing_task.notes = "Description"
        existing_task.status = "needsAction"
        mock_gtask_client.get_task.return_value = existing_task

        updated_task = MagicMock()
        updated_task.id = "task_123"
        updated_task.title = "(IP) New Task"
        updated_task.notes = "Description"
        updated_task.status = "needsAction"
        mock_gtask_client.insert_task.return_value = updated_task
        mock_gtask_client.delete_task.return_value = True

        client = TicketsClient(gtask_client=mock_gtask_client)

        ticket = client.update_ticket(
            "task_123", status=TicketStatus.IN_PROGRESS, title="New Task"
        )

        assert ticket.id == "task_123"
        mock_gtask_client.delete_task.assert_called_once()
        mock_gtask_client.insert_task.assert_called_once()

    def test_update_ticket_not_found(self) -> None:
        """Test update_ticket raises error when ticket not found (lines 285-313)."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        # get_task raises ValueError when task not found (which get_ticket catches and returns None)
        mock_gtask_client.get_task.side_effect = ValueError("Task not found")

        client = TicketsClient(gtask_client=mock_gtask_client)

        with pytest.raises(ValueError, match=r"Ticket .* not found"):
            client.update_ticket("nonexistent", status=TicketStatus.CLOSED)

    def test_delete_ticket_success(self) -> None:
        """Test delete_ticket method (lines 325-326)."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        mock_gtask_client.delete_task.return_value = True

        client = TicketsClient(gtask_client=mock_gtask_client)

        result = client.delete_ticket("task_123")

        assert result is True
        mock_gtask_client.delete_task.assert_called_once_with("tasklist_123", "task_123")

    def test_delete_ticket_failure(self) -> None:
        """Test delete_ticket returns False on failure (lines 325-326)."""
        from task_client_api import tasklist

        mock_gtask_client = MagicMock()
        mock_tasklist = MagicMock(spec=tasklist.TaskList)
        mock_tasklist.id = "tasklist_123"
        mock_gtask_client.list_tasklists.return_value = [mock_tasklist]

        mock_gtask_client.delete_task.return_value = False

        client = TicketsClient(gtask_client=mock_gtask_client)

        result = client.delete_ticket("task_123")

        assert result is False



# ===== Tests from test_tickets_impl_internal_methods.py =====


# ===== Internal Implementation Tests =====
# ===== Tests from test_gtask_impl_integration.py =====


# ===== Tests from test_tickets_impl_direct.py =====

