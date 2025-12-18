"""Integration with tickets_client_impl for executing ticket operations."""

import logging
from typing import Any

import gtask_client_impl  # noqa: F401
from tickets_api import Ticket, TicketStatus
from tickets_client_impl import TicketsClient

gtask_client_impl.register()

logger = logging.getLogger(__name__)


class TicketsIntegration:
    """Wrapper around TicketsClient for executing ticket operations."""

    def __init__(self) -> None:
        """Initialize the tickets integration."""
        self._client: TicketsClient | None = None

    def _get_client(self) -> TicketsClient:
        """Get or create the tickets client.

        Returns:
            TicketsClient instance.

        """
        if self._client is None:
            logger.info("Initializing TicketsClient (non-interactive mode)")
            self._client = TicketsClient(interactive=False)
            logger.info("TicketsClient initialized successfully")
        return self._client

    def execute_command(
        self, command_name: str, args: list[str]
    ) -> tuple[bool, str, Any]:
        """Execute a ticket command.

        Args:
            command_name: The command name (e.g., 'get_tickets').
            args: The command arguments.

        Returns:
            Tuple of (success, message, data) where:
            - success: Whether the command executed successfully
            - message: Human-readable message
            - data: Command result data (ticket, list of tickets, etc.)

        """
        client = self._get_client()

        try:
            if command_name == "get_tickets":
                return self._handle_get_tickets(client, args)
            elif command_name == "create_ticket":
                return self._handle_create_ticket(client, args)
            elif command_name == "get_ticket":
                return self._handle_get_ticket(client, args)
            elif command_name == "update_ticket":
                return self._handle_update_ticket(client, args)
            elif command_name == "delete_ticket":
                return self._handle_delete_ticket(client, args)
            else:
                return False, f"Unknown command: {command_name}", None
        except Exception as e:
            logger.exception("Error executing ticket command: %s", e)
            return False, f"Error executing command: {str(e)}", None

    def _handle_get_tickets(
        self, client: TicketsClient, args: list[str]
    ) -> tuple[bool, str, Any]:
        """Handle get_tickets command.

        Args:
            client: The tickets client.
            args: Command arguments [query?, status?].

        Returns:
            Tuple of (success, message, tickets).

        """
        query = args[0] if len(args) > 0 and args[0] else None
        status_str = args[1] if len(args) > 1 and args[1] else None

        # Parse status string
        status = None
        if status_str:
            status_lower = status_str.lower().strip()
            status_map = {
                "open": TicketStatus.OPEN,
                "in_progress": TicketStatus.IN_PROGRESS,
                "inprogress": TicketStatus.IN_PROGRESS,
                "closed": TicketStatus.CLOSED,
            }
            status = status_map.get(status_lower)

        tickets = client.search_tickets(query=query, status=status)

        if not tickets:
            return True, "No tickets found matching your criteria.", []

        message = f"Found {len(tickets)} ticket(s):\n"
        for ticket in tickets:
            message += f"- [{ticket.id}] {ticket.title} ({ticket.status.value})\n"

        return True, message, tickets

    def _handle_create_ticket(
        self, client: TicketsClient, args: list[str]
    ) -> tuple[bool, str, Any]:
        """Handle create_ticket command.

        Args:
            client: The tickets client.
            args: Command arguments [title, description].

        Returns:
            Tuple of (success, message, ticket).

        """
        if len(args) < 2:
            return False, "create_ticket requires title and description arguments.", None

        title = args[0].strip('"\'')
        description = args[1].strip('"\'')

        ticket = client.create_ticket(title=title, description=description)

        message = f"Created ticket [{ticket.id}]: {ticket.title}"
        return True, message, ticket

    def _handle_get_ticket(
        self, client: TicketsClient, args: list[str]
    ) -> tuple[bool, str, Any]:
        """Handle get_ticket command.

        Args:
            client: The tickets client.
            args: Command arguments [ticket_id].

        Returns:
            Tuple of (success, message, ticket).

        """
        if len(args) < 1:
            return False, "get_ticket requires a ticket_id argument.", None

        ticket_id = args[0].strip('"\'')

        ticket = client.get_ticket(ticket_id)

        if not ticket:
            return False, f"Ticket {ticket_id} not found.", None

        message = (
            f"Ticket [{ticket.id}]:\n"
            f"Title: {ticket.title}\n"
            f"Status: {ticket.status.value}\n"
            f"Description: {ticket.description}"
        )
        return True, message, ticket

    def _handle_update_ticket(
        self, client: TicketsClient, args: list[str]
    ) -> tuple[bool, str, Any]:
        """Handle update_ticket command.

        Args:
            client: The tickets client.
            args: Command arguments [ticket_id, status?, title?].

        Returns:
            Tuple of (success, message, ticket).

        """
        if len(args) < 1:
            return False, "update_ticket requires at least a ticket_id argument.", None

        ticket_id = args[0].strip('"\'')
        status_str = args[1] if len(args) > 1 and args[1] else None
        title = args[2] if len(args) > 2 and args[2] else None

        # Parse status string
        status = None
        if status_str:
            status_lower = status_str.lower().strip()
            status_map = {
                "open": TicketStatus.OPEN,
                "in_progress": TicketStatus.IN_PROGRESS,
                "inprogress": TicketStatus.IN_PROGRESS,
                "closed": TicketStatus.CLOSED,
            }
            status = status_map.get(status_lower)
        title_clean = title.strip('"\'') if title else None

        ticket = client.update_ticket(
            ticket_id=ticket_id, status=status, title=title_clean
        )

        message = f"Updated ticket [{ticket.id}]: {ticket.title} ({ticket.status.value})"
        return True, message, ticket

    def _handle_delete_ticket(
        self, client: TicketsClient, args: list[str]
    ) -> tuple[bool, str, Any]:
        """Handle delete_ticket command.

        Args:
            client: The tickets client.
            args: Command arguments [ticket_id].

        Returns:
            Tuple of (success, message, None).

        """
        if len(args) < 1:
            return False, "delete_ticket requires a ticket_id argument.", None

        ticket_id = args[0].strip('"\'')

        success = client.delete_ticket(ticket_id)

        if success:
            return True, f"Ticket {ticket_id} deleted successfully.", None
        return False, f"Failed to delete ticket {ticket_id}.", None

