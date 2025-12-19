"""Integration tests for AI → Discord Flow: AI response generation and sending to Discord.

This file consolidates tests from the following source files:
  - test_main_routing_integration.py
  - test_routing_coverage.py

All external services are mocked.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from main_service.main import (
    _filter_new_messages,
    _process_new_message,
    _process_new_messages,
)
from main_service.routing import _validate_command_response

from main_service import routing

pytestmark = pytest.mark.integration
class TestMainRoutingIntegration:
    """Test integration between main service and routing components."""

    def test_process_message_with_ticket_command(
        self,
        mock_discord_client: MagicMock,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that messages with ticket commands are processed correctly.

        This test verifies:
        1. Message is received from Discord
        2. AI extracts ticket commands from message
        3. Commands are executed via ticketing
        4. AI generates response
        5. Response is sent back to Discord
        """
        # Setup: Mock message
        mock_message = MagicMock()
        mock_message.id = "msg_123"
        mock_message.content = "Create a ticket for testing"
        mock_message.sender_id = "user_456"
        mock_message.channel_id = "channel_789"

        # Setup: Mock AI extraction
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

        # Setup: Mock ticket creation
        from tickets_api import Ticket, TicketStatus

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = "ticket_123"
        mock_ticket.title = "Test Ticket"
        mock_ticket.description = "Testing"
        mock_ticket.status = TicketStatus.OPEN
        mock_ticket.assignee = None
        mock_tickets_client.create_ticket.return_value = mock_ticket

        # Execute: Process message
        seen_message_ids: set[str] = set()
        _process_new_message(
            client=mock_discord_client,
            msg=mock_message,
            channel_id="channel_789",
            seen_message_ids=seen_message_ids,
            ticket_client=mock_tickets_client,
        )

        # Verify: AI was called for extraction and response
        assert mock_ai_client.generate_response.call_count >= 2

        # Verify: Ticket was created
        mock_tickets_client.create_ticket.assert_called_once()

        # Verify: Response was sent to Discord
        mock_discord_client.send_message.assert_called_once()
        call_args = mock_discord_client.send_message.call_args
        assert call_args[1]["channel_id"] == "channel_789"
        assert isinstance(call_args[1]["content"], str)
        assert len(call_args[1]["content"]) > 0

        # Verify: Message was marked as seen
        assert "msg_123" in seen_message_ids

    def test_process_message_without_ticket_command(
        self,
        mock_discord_client: MagicMock,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test that regular messages (without commands) are handled correctly."""
        # Setup: Mock message without ticket command
        mock_message = MagicMock()
        mock_message.id = "msg_456"
        mock_message.content = "Hello, how are you?"
        mock_message.sender_id = "user_789"
        mock_message.channel_id = "channel_123"

        # Setup: Mock AI (no commands extracted, but generates response)
        mock_ai_client.generate_response.side_effect = [
            # Command extraction (returns empty)
            {"actions": []},
            # Response generation
            "Hello! I'm doing well, thank you for asking.",
        ]

        # Execute
        seen_message_ids: set[str] = set()
        _process_new_message(
            client=mock_discord_client,
            msg=mock_message,
            channel_id="channel_123",
            seen_message_ids=seen_message_ids,
            ticket_client=mock_tickets_client,
        )

        # Verify: AI was called
        assert mock_ai_client.generate_response.called

        # Verify: Response was sent
        mock_discord_client.send_message.assert_called_once()

        # Verify: No ticket operations
        mock_tickets_client.create_ticket.assert_not_called()

    def test_filter_new_messages_excludes_seen_and_bot_messages(
        self,
        mock_discord_client: MagicMock,
    ) -> None:
        """Test that message filtering correctly excludes seen and bot messages."""
        # Setup: Mock messages (using MagicMock directly since Message is abstract)
        msg1 = MagicMock()
        msg1.id = "msg_1"
        msg1.sender_id = "user_1"
        msg1.content = "Message 1"

        msg2 = MagicMock()
        msg2.id = "msg_2"
        msg2.sender_id = "bot_123"  # Bot message
        msg2.content = "Bot response"

        msg3 = MagicMock()
        msg3.id = "msg_3"
        msg3.sender_id = "user_2"
        msg3.content = "Message 3"

        messages = [msg1, msg2, msg3]
        seen_message_ids = {"msg_1"}  # msg_1 already seen
        bot_user_id = "bot_123"

        # Execute
        new_messages = _filter_new_messages(messages, seen_message_ids, bot_user_id)

        # Verify: Only msg_3 is new (msg_1 is seen, msg_2 is from bot)
        assert len(new_messages) == 1
        assert new_messages[0].id == "msg_3"

    def test_process_new_messages_handles_multiple_messages(
        self,
        mock_discord_client: MagicMock,
        mock_ai_client: MagicMock,
        mock_tickets_client: MagicMock,
    ) -> None:
        """Test processing multiple new messages."""
        # Setup: Mock messages (using MagicMock directly)
        msg1 = MagicMock()
        msg1.id = "msg_1"
        msg1.content = "Create ticket 1"
        msg1.sender_id = "user_1"

        msg2 = MagicMock()
        msg2.id = "msg_2"
        msg2.content = "Create ticket 2"
        msg2.sender_id = "user_2"

        new_messages = [msg1, msg2]
        seen_message_ids: set[str] = set()
        channel_id = "channel_123"

        # Setup: Mock AI responses
        mock_ai_client.generate_response.side_effect = [
            # Extraction for msg1
            {
                "actions": [
                    {
                        "type": "create_ticket",
                        "params": {
                            "title": "Ticket 1",
                            "description": "Desc 1",
                            "ticket_id": None,
                            "status": None,
                            "query": None,
                            "assignee": None,
                        },
                    }
                ]
            },
            # Response for msg1
            "Created ticket 1",
            # Extraction for msg2
            {
                "actions": [
                    {
                        "type": "create_ticket",
                        "params": {
                            "title": "Ticket 2",
                            "description": "Desc 2",
                            "ticket_id": None,
                            "status": None,
                            "query": None,
                            "assignee": None,
                        },
                    }
                ]
            },
            # Response for msg2
            "Created ticket 2",
        ]

        # Setup: Mock ticket creation
        from tickets_api import Ticket, TicketStatus

        def create_ticket_side_effect(title: str, description: str, assignee: str | None = None) -> MagicMock:
            ticket = MagicMock(spec=Ticket)
            ticket.id = f"ticket_{title.lower().replace(' ', '_')}"
            ticket.title = title
            ticket.description = description
            ticket.status = TicketStatus.OPEN
            ticket.assignee = assignee
            return ticket

        mock_tickets_client.create_ticket.side_effect = create_ticket_side_effect

        # Setup: Mock get_messages for re-fetch
        mock_discord_client.get_messages.return_value = [msg1, msg2]

        # Execute
        updated_messages = _process_new_messages(
            client=mock_discord_client,
            new_messages=new_messages,
            channel_id=channel_id,
            seen_message_ids=seen_message_ids,
            message_check_limit=10,
            ticket_client=mock_tickets_client,
        )

        # Verify: Both messages were processed
        assert mock_discord_client.send_message.call_count == 2
        assert "msg_1" in seen_message_ids
        assert "msg_2" in seen_message_ids
        assert len(updated_messages) == 2


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

