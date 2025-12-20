"""Direct integration tests for TicketsClient implementation.

Tests directly instantiate TicketsClient with mocked GTaskClient to cover
internal implementation details and edge cases.

Improve coverage for tickets_impl.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from tickets_client_impl.tickets_impl import _TaskBuilder

from tickets_api import TicketStatus
from tickets_client_impl import TicketsClient

pytestmark = pytest.mark.integration


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

        assert len(tickets) == 2  # noqa: PLR2004
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

        ticket = client.update_ticket("task_123", status=TicketStatus.IN_PROGRESS, title="New Task")

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
