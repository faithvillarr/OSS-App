"""Integration tests for AI → Ticketing Flow: AI command extraction and ticketing execution.

This file consolidates tests from the following source files:
  - test_routing_ticketing_integration.py
  - test_routing_coverage.py
  - test_main_service_client_integration.py

All external services are mocked.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from main_service.main import (
    _initialize_ai_client,
    _initialize_ticket_client,
    _process_new_message,
)
from main_service.routing import _validate_command_response

from main_service import routing, ticketing
from tickets_api import Ticket, TicketStatus

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


# ===== Tests from test_routing_coverage.py =====


class TestRoutingCoverage:
    """Additional tests for routing module coverage."""

    def test_extract_commands_validation_failure_retry(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test extract_commands with validation failure and retry."""
        # First call: invalid response
        # Second call: valid response
        mock_ai_client.generate_response.side_effect = [
            {"invalid": "response"},  # Invalid - missing "actions"
            {
                "actions": [
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
            },
        ]

        commands = routing.extract_commands("Create a ticket")

        assert len(commands) == 1
        assert commands[0]["type"] == "create_ticket"
        assert mock_ai_client.generate_response.call_count == 2

    def test_extract_commands_max_retries_exceeded(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test extract_commands when max retries are exceeded."""
        # All calls return invalid response
        mock_ai_client.generate_response.return_value = {"invalid": "response"}

        commands = routing.extract_commands("Create a ticket")

        assert len(commands) == 0
        assert mock_ai_client.generate_response.call_count == 3  # max_retries

    def test_extract_commands_exception_handling(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test extract_commands exception handling."""
        mock_ai_client.generate_response.side_effect = Exception("AI Error")

        commands = routing.extract_commands("Create a ticket")

        assert len(commands) == 0

    def test_correct_commands_success(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test correct_commands with successful correction."""
        original_commands = [
            {
                "type": "create_ticket",
                "params": {"title": "Test", "description": ""},
            }
        ]

        mock_ai_client.generate_response.return_value = {
            "actions": [
                {
                    "type": "create_ticket",
                    "params": {
                        "title": "Test",
                        "description": "Fixed Description",
                        "ticket_id": None,
                        "status": None,
                        "query": None,
                        "assignee": None,
                    },
                }
            ]
        }

        corrected = routing.correct_commands(original_commands, "Missing description")

        assert len(corrected) == 1
        assert corrected[0]["params"]["description"] == "Fixed Description"

    def test_correct_commands_validation_failure(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test correct_commands with validation failure."""
        original_commands = [
            {
                "type": "create_ticket",
                "params": {"title": "Test", "description": ""},
            }
        ]

        # All attempts return invalid response
        mock_ai_client.generate_response.return_value = {"invalid": "response"}

        corrected = routing.correct_commands(original_commands, "Error")

        # Should return original commands when correction fails
        assert corrected == original_commands

    def test_correct_commands_exception(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test correct_commands when exception occurs."""
        original_commands = [
            {
                "type": "create_ticket",
                "params": {"title": "Test", "description": ""},
            }
        ]

        mock_ai_client.generate_response.side_effect = Exception("AI Error")

        corrected = routing.correct_commands(original_commands, "Error")

        # Should return original commands when exception occurs
        assert corrected == original_commands

    def test_generate_response_exception(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test generate_response when exception occurs."""
        mock_ai_client.generate_response.side_effect = Exception("AI Error")

        results = [
            {
                "success": True,
                "command": {"type": "create_ticket", "params": {}},
                "result": {"id": "ticket_123"},
                "error": None,
            }
        ]

        response = routing.generate_response("Create ticket", results)

        assert "error" in response.lower() or "encountered" in response.lower()

    def test_generate_response_non_string(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test generate_response when AI returns non-string."""
        mock_ai_client.generate_response.return_value = {"not": "a string"}

        results = [
            {
                "success": True,
                "command": {"type": "create_ticket", "params": {}},
                "result": {"id": "ticket_123"},
                "error": None,
            }
        ]

        response = routing.generate_response("Create ticket", results)

        assert isinstance(response, str)
        assert len(response) > 0

    def test_execute_commands_iteratively_no_followup(
        self,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test iterative execution when AI determines no follow-up needed."""
        from tickets_api import Ticket, TicketStatus

        # Mock AI response for follow-up (no more commands needed)
        # This will be called after the initial command is executed
        mock_ai_client.generate_response.return_value = {"actions": []}

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Test"
        mock_ticket.description = "Test"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.create_ticket.return_value = mock_ticket

        results = routing.execute_commands_iteratively(
            user_message="Create a ticket",
            initial_commands=[
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
            ],
            ticket_client=mock_tickets_client,
            max_iterations=3,
        )

        # Should have executed the initial command
        # After execution, AI is asked for follow-up and returns empty actions
        # So we should have at least 1 result (the initial command)
        assert len(results) >= 1
        # Check that at least one result is successful
        successful_results = [r for r in results if r.get("success")]
        assert len(successful_results) >= 1
        assert successful_results[0]["command"]["type"] == "create_ticket"

    def test_execute_commands_iteratively_max_iterations(
        self,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test iterative execution when max iterations is reached."""
        from tickets_api import Ticket, TicketStatus

        # AI keeps generating follow-up commands
        mock_ai_client.generate_response.side_effect = [
            # Follow-up commands (multiple iterations)
            {
                "actions": [
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
            },
            {
                "actions": [
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
            },
        ]

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Test"
        mock_ticket.description = "Test"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.create_ticket.return_value = mock_ticket
        mock_tickets_client.search_tickets.return_value = []

        results = routing.execute_commands_iteratively(
            user_message="Create and search tickets",
            initial_commands=[
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
            ],
            ticket_client=mock_tickets_client,
            max_iterations=2,  # Low max to trigger limit
        )

        # Should have executed initial command and some follow-ups
        assert len(results) >= 1

    def test_validate_command_response_invalid_structure(
        self,
    ) -> None:
        """Test _validate_command_response with invalid structure."""
        # Import the private function for testing

        # Not a dict
        is_valid, error = _validate_command_response("not a dict")
        assert is_valid is False
        assert error is not None

        # Missing "actions"
        is_valid, error = _validate_command_response({"no_actions": True})
        assert is_valid is False
        assert "actions" in error.lower()

        # "actions" is not a list
        is_valid, error = _validate_command_response({"actions": "not a list"})
        assert is_valid is False
        assert "list" in error.lower()

    def test_validate_command_response_invalid_action(
        self,
    ) -> None:
        """Test _validate_command_response with invalid action."""
        # Action missing "type"
        response = {"actions": [{"params": {}}]}
        is_valid, error = _validate_command_response(response)
        assert is_valid is False
        assert "type" in error.lower()

        # Action missing "params"
        response = {"actions": [{"type": "create_ticket"}]}
        is_valid, error = _validate_command_response(response)
        assert is_valid is False
        assert "params" in error.lower()

        # Invalid command type
        response = {
            "actions": [
                {
                    "type": "invalid_command",
                    "params": {},
                }
            ]
        }
        is_valid, error = _validate_command_response(response)
        assert is_valid is False
        assert "invalid" in error.lower()

        # "params" is not a dict
        response = {
            "actions": [
                {
                    "type": "create_ticket",
                    "params": "not a dict",
                }
            ]
        }
        is_valid, error = _validate_command_response(response)
        assert is_valid is False
        assert "dict" in error.lower()


# ===== Tests from test_main_service_client_integration.py =====


class TestMainServiceChatClientIntegration:
    """Test integration between main_service and chat_api/discord_client_impl."""

    def test_chat_api_get_client_integration(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test that main_service correctly uses chat_api.get_client().

        This verifies the integration between main_service and the chat_api
        abstraction layer, which returns discord_client_impl.
        """
        import chat_api

        # Mock chat_api.get_client to return our mock Discord client
        with patch("chat_api.get_client", return_value=mock_discord_client):
            client = chat_api.get_client()

            # Verify it's the mocked client
            assert client is mock_discord_client

            # Verify main_service can use it
            mock_discord_client.get_messages.return_value = []
            messages = client.get_messages(channel_id="channel_123", limit=10)

            assert messages == []
            mock_discord_client.get_messages.assert_called_once_with(
                channel_id="channel_123", limit=10
            )

    def test_process_message_uses_chat_interface(
        self,
        mock_discord_client: MagicMock,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that _process_new_message correctly uses ChatInterface."""
        # Create a mock message
        mock_message = MagicMock()
        mock_message.id = "msg_123"
        mock_message.content = "Create a ticket for testing"
        mock_message.sender_id = "user_456"

        # Mock AI responses
        mock_ai_client.generate_response.side_effect = [
            # Command extraction
            {
                "actions": [
                    {
                        "type": "create_ticket",
                        "params": {
                            "title": "Test Ticket",
                            "description": "Testing",
                            "ticket_id": None,
                            "status": None,
                            "query": None,
                            "assignee": None,
                        },
                    }
                ]
            },
            # Response generation
            "I've created ticket ticket_123: Test Ticket",
        ]

        # Mock ticket creation
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Test Ticket"
        mock_ticket.description = "Testing"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.create_ticket.return_value = mock_ticket

        # Execute
        seen_message_ids: set[str] = set()
        _process_new_message(
            client=mock_discord_client,
            msg=mock_message,
            channel_id="channel_789",
            seen_message_ids=seen_message_ids,
            ticket_client=mock_tickets_client,
        )

        # Verify ChatInterface methods were called
        mock_discord_client.send_message.assert_called_once()
        call_args = mock_discord_client.send_message.call_args
        assert call_args[1]["channel_id"] == "channel_789"
        assert isinstance(call_args[1]["content"], str)


class TestMainServiceTicketsClientIntegration:
    """Test integration between main_service and tickets_client_impl."""

    def test_tickets_client_initialization(
        self,
    ) -> None:
        """Test that _initialize_ticket_client correctly initializes TicketsClient."""
        from tickets_client_impl import TicketsClient

        # Mock TicketsClient initialization
        with patch("main_service.main.TicketsClient") as mock_tickets_class:
            mock_client_instance = MagicMock(spec=TicketsClient)
            # Mock the _gtask_client attribute and its list_tasklists method
            mock_gtask_client = MagicMock()
            mock_gtask_client.list_tasklists.return_value = [
                {"id": "list1", "title": "Task List 1"}
            ]
            mock_client_instance._gtask_client = mock_gtask_client
            mock_tickets_class.return_value = mock_client_instance

            # Execute
            ticket_client = _initialize_ticket_client()

            # Verify
            assert ticket_client is mock_client_instance
            mock_tickets_class.assert_called_once_with(interactive=False)
            # Verify health check was called
            mock_gtask_client.list_tasklists.assert_called_once()

    def test_ticketing_execute_commands_uses_tickets_client(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that ticketing.execute_commands correctly uses TicketsClient."""
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Test Ticket"
        mock_ticket.description = "Test Description"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.create_ticket.return_value = mock_ticket

        # Execute command
        commands = [
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

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify TicketsClient was called correctly
        mock_tickets_client.create_ticket.assert_called_once_with(
            title="Test Ticket",
            description="Test Description",
            assignee=None,
        )

        # Verify results
        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["result"]["id"] == "ticket_123"

    def test_ticketing_with_all_ticket_operations(
        self,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that ticketing module works with all TicketsClient operations."""
        from tickets_api import Ticket, TicketStatus

        # Setup mocks for all operations
        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Test Ticket"
        mock_ticket.description = "Description"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None

        mock_tickets_client.create_ticket.return_value = mock_ticket
        mock_tickets_client.get_ticket.return_value = mock_ticket
        mock_tickets_client.search_tickets.return_value = [mock_ticket]
        mock_tickets_client.update_ticket.return_value = mock_ticket
        mock_tickets_client.delete_ticket.return_value = True

        # Test all command types
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
            },
            {
                "type": "get_ticket",
                "params": {"ticket_id": "ticket_123"},
            },
            {
                "type": "search_tickets",
                "params": {"query": "test"},
            },
            {
                "type": "update_ticket",
                "params": {"ticket_id": "ticket_123", "status": "in_progress"},
            },
            {
                "type": "delete_ticket",
                "params": {"ticket_id": "ticket_123"},
            },
        ]

        results = ticketing.execute_commands(commands, mock_tickets_client)

        # Verify all operations were called
        assert len(results) == 5
        assert all(r["success"] for r in results)
        mock_tickets_client.create_ticket.assert_called_once()
        mock_tickets_client.get_ticket.assert_called_once()
        mock_tickets_client.search_tickets.assert_called_once()
        mock_tickets_client.update_ticket.assert_called_once()
        mock_tickets_client.delete_ticket.assert_called_once()


class TestMainServiceAIClientIntegration:
    """Test integration between main_service and ai_api/openai_impl."""

    def test_ai_client_initialization(
        self,
    ) -> None:
        """Test that _initialize_ai_client correctly initializes AI client."""
        # Mock AI client
        mock_ai_client = MagicMock()
        mock_ai_client.generate_response = MagicMock()

        with patch("main_service.main.ai_api.get_client", return_value=mock_ai_client):
            ai_client = _initialize_ai_client()

            # Verify
            assert ai_client is mock_ai_client
            assert hasattr(ai_client, "generate_response")
            assert callable(ai_client.generate_response)

    def test_routing_extract_commands_uses_ai_client(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test that routing.extract_commands correctly uses AI client."""
        mock_ai_client.generate_response.return_value = {
            "actions": [
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
        }

        commands = routing.extract_commands("Create a ticket for testing")

        # Verify AI client was called
        assert mock_ai_client.generate_response.called

        # Verify commands extracted
        assert len(commands) == 1
        assert commands[0]["type"] == "create_ticket"

    def test_routing_generate_response_uses_ai_client(
        self,
        mock_ai_client: MagicMock,
    ) -> None:
        """Test that routing.generate_response correctly uses AI client."""
        mock_ai_client.generate_response.return_value = (
            "I've successfully created ticket ticket_123: Test Ticket"
        )

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

        response = routing.generate_response("Create a ticket", results)

        # Verify AI client was called
        assert mock_ai_client.generate_response.called

        # Verify response
        assert isinstance(response, str)
        assert len(response) > 0


class TestMainServiceFullIntegration:
    """Test full integration flow across all components."""

    def test_full_message_processing_flow(
        self,
        mock_discord_client: MagicMock,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test the complete flow from message to response.

        This tests the integration of:
        1. Chat client (Discord) receives message
        2. AI client extracts commands
        3. Tickets client executes commands
        4. AI client generates response
        5. Chat client sends response
        """
        from tickets_api import Ticket, TicketStatus

        # Setup: Mock message
        mock_message = MagicMock()
        mock_message.id = "msg_123"
        mock_message.content = "Create a ticket for testing and then search for it"
        mock_message.sender_id = "user_456"

        # Setup: Mock AI responses
        mock_ai_client.generate_response.side_effect = [
            # Initial command extraction
            {
                "actions": [
                    {
                        "type": "create_ticket",
                        "params": {
                            "title": "Test Ticket",
                            "description": "Testing",
                            "ticket_id": None,
                            "status": None,
                            "query": None,
                            "assignee": None,
                        },
                    },
                    {
                        "type": "search_tickets",
                        "params": {
                            "query": "Test",
                            "status": None,
                            "ticket_id": None,
                            "title": None,
                            "description": None,
                            "assignee": None,
                        },
                    },
                ]
            },
            # Follow-up (no more commands)
            {"actions": []},
            # Response generation
            "I've created ticket ticket_123 and found 1 matching ticket.",
        ]

        # Setup: Mock ticket operations
        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Test Ticket"
        mock_ticket.description = "Testing"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None

        mock_tickets_client.create_ticket.return_value = mock_ticket
        mock_tickets_client.search_tickets.return_value = [mock_ticket]

        # Execute: Process message
        seen_message_ids: set[str] = set()
        _process_new_message(
            client=mock_discord_client,
            msg=mock_message,
            channel_id="channel_789",
            seen_message_ids=seen_message_ids,
            ticket_client=mock_tickets_client,
        )

        # Verify: All components were used
        # 1. AI was called for extraction
        assert mock_ai_client.generate_response.call_count >= 2

        # 2. Tickets client was called
        mock_tickets_client.create_ticket.assert_called_once()
        mock_tickets_client.search_tickets.assert_called_once()

        # 3. Response was sent via chat client
        mock_discord_client.send_message.assert_called_once()

        # 4. Message was marked as seen
        assert "msg_123" in seen_message_ids

