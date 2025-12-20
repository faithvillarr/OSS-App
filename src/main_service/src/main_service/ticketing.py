"""Ticket command execution and formatting."""

import logging
from typing import Any

import tickets_client_impl  # noqa: F401
from tickets_api import Ticket, TicketInterface, TicketStatus

logger = logging.getLogger(__name__)


def execute_commands(commands: list[dict[str, Any]], ticket_client: TicketInterface) -> list[dict[str, Any]]:
    """Execute ticket commands and return standardized results.

    Args:
        commands: List of command dictionaries, each with "type" and "params" keys.
        ticket_client: The ticket client interface to use for operations.

    Returns:
        List of result dictionaries, each containing:
            - "success": bool
            - "command": dict (the original command)
            - "result": dict | None (formatted ticket data if successful)
            - "error": str | None (error message if failed)

    """
    results = []

    logger.info("Executing %d ticket command(s)", len(commands))

    for i, command in enumerate(commands, 1):
        command_type = command.get("type")
        params = command.get("params", {})

        logger.info("Command %d/%d: type=%s, params=%s", i, len(commands), command_type, params)

        try:
            if command_type == "create_ticket":
                result = _execute_create_ticket(params, ticket_client)
            elif command_type == "get_ticket":
                result = _execute_get_ticket(params, ticket_client)
            elif command_type == "search_tickets":
                result = _execute_search_tickets(params, ticket_client)
            elif command_type == "update_ticket":
                result = _execute_update_ticket(params, ticket_client)
            elif command_type == "delete_ticket":
                result = _execute_delete_ticket(params, ticket_client)
            else:
                result = {
                    "success": False,
                    "command": command,
                    "result": None,
                    "error": f"Unknown command type: {command_type}",
                }

            if result.get("success"):
                logger.info("Command %d/%d succeeded", i, len(commands))
            else:
                logger.warning("Command %d/%d failed: %s", i, len(commands), result.get("error", "Unknown error"))

            results.append(result)
        except Exception as e:
            logger.exception("Error executing command %s", command_type)
            results.append(
                {
                    "success": False,
                    "command": command,
                    "result": None,
                    "error": str(e),
                }
            )

    return results


def format_ticket_for_json(ticket: Ticket) -> dict[str, Any]:
    """Convert a Ticket object to standardized JSON format.

    Args:
        ticket: The Ticket object to format.

    Returns:
        Dictionary with keys: id, title, description, status, assignee.

    """
    return {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "status": ticket.status.value,  # Convert enum to string
        "assignee": ticket.assignee,
    }


def _execute_create_ticket(params: dict[str, Any], ticket_client: TicketInterface) -> dict[str, Any]:
    """Execute create_ticket command.

    Args:
        params: Command parameters with "title", "description", and optionally "assignee".
        ticket_client: The ticket client interface.

    Returns:
        Result dictionary.

    """
    title = params.get("title")
    description = params.get("description")
    assignee = params.get("assignee")

    if not title or not description:
        return {
            "success": False,
            "command": {"type": "create_ticket", "params": params},
            "result": None,
            "error": "Missing required parameters: title and description are required",
        }

    try:
        logger.info("Calling ticket_client.create_ticket(title=%s, description=%s, assignee=%s)", title, description, assignee)
        ticket = ticket_client.create_ticket(
            title=str(title),
            description=str(description),
            assignee=str(assignee) if assignee else None,
        )
        logger.info("create_ticket returned ticket with id=%s", ticket.id)
        return {
            "success": True,
            "command": {"type": "create_ticket", "params": params},
            "result": format_ticket_for_json(ticket),
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "command": {"type": "create_ticket", "params": params},
            "result": None,
            "error": str(e),
        }


def _execute_get_ticket(params: dict[str, Any], ticket_client: TicketInterface) -> dict[str, Any]:
    """Execute get_ticket command.

    Args:
        params: Command parameters with "ticket_id".
        ticket_client: The ticket client interface.

    Returns:
        Result dictionary.

    """
    ticket_id = params.get("ticket_id")

    if not ticket_id:
        return {
            "success": False,
            "command": {"type": "get_ticket", "params": params},
            "result": None,
            "error": "Missing required parameter: ticket_id",
        }

    try:
        logger.info("Calling ticket_client.get_ticket(ticket_id=%s)", ticket_id)
        ticket = ticket_client.get_ticket(str(ticket_id))
        if ticket is None:
            logger.warning("get_ticket returned None for ticket_id=%s", ticket_id)
            return {
                "success": False,
                "command": {"type": "get_ticket", "params": params},
                "result": None,
                "error": f"Ticket with ID '{ticket_id}' not found",
            }

        logger.info("get_ticket returned ticket with id=%s, title=%s", ticket.id, ticket.title)
        return {
            "success": True,
            "command": {"type": "get_ticket", "params": params},
            "result": format_ticket_for_json(ticket),
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "command": {"type": "get_ticket", "params": params},
            "result": None,
            "error": str(e),
        }


def _execute_search_tickets(params: dict[str, Any], ticket_client: TicketInterface) -> dict[str, Any]:
    """Execute search_tickets command.

    Args:
        params: Command parameters with optional "query" and "status".
        ticket_client: The ticket client interface.

    Returns:
        Result dictionary.

    """
    query = params.get("query")
    status_str = params.get("status")

    # Convert status string to TicketStatus enum if provided
    status = None
    if status_str:
        try:
            status = TicketStatus(status_str.lower())
        except ValueError:
            return {
                "success": False,
                "command": {"type": "search_tickets", "params": params},
                "result": None,
                "error": f"Invalid status value: {status_str}. Must be 'open', 'in_progress', or 'closed'",
            }

    try:
        logger.info("Calling ticket_client.search_tickets(query=%s, status=%s)", query, status)
        tickets = ticket_client.search_tickets(
            query=str(query) if query else None,
            status=status,
        )
        logger.info("search_tickets returned %d ticket(s)", len(tickets))

        # Format all tickets
        formatted_tickets = [format_ticket_for_json(ticket) for ticket in tickets]

        return {
            "success": True,
            "command": {"type": "search_tickets", "params": params},
            "result": {"tickets": formatted_tickets, "count": len(formatted_tickets)},
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "command": {"type": "search_tickets", "params": params},
            "result": None,
            "error": str(e),
        }


def _execute_update_ticket(params: dict[str, Any], ticket_client: TicketInterface) -> dict[str, Any]:
    """Execute update_ticket command.

    Args:
        params: Command parameters with "ticket_id" and optionally "status" and "title".
        ticket_client: The ticket client interface.

    Returns:
        Result dictionary.

    """
    ticket_id = params.get("ticket_id")
    status_str = params.get("status")
    title = params.get("title")

    if not ticket_id:
        return {
            "success": False,
            "command": {"type": "update_ticket", "params": params},
            "result": None,
            "error": "Missing required parameter: ticket_id",
        }

    if not status_str and not title:
        return {
            "success": False,
            "command": {"type": "update_ticket", "params": params},
            "result": None,
            "error": "At least one of 'status' or 'title' must be provided",
        }

    # Convert status string to TicketStatus enum if provided
    status = None
    if status_str:
        try:
            status = TicketStatus(status_str.lower())
        except ValueError:
            return {
                "success": False,
                "command": {"type": "update_ticket", "params": params},
                "result": None,
                "error": f"Invalid status value: {status_str}. Must be 'open', 'in_progress', or 'closed'",
            }

    try:
        logger.info("Calling ticket_client.update_ticket(ticket_id=%s, status=%s, title=%s)", ticket_id, status, title)
        ticket = ticket_client.update_ticket(
            ticket_id=str(ticket_id),
            status=status,
            title=str(title) if title else None,
        )
        logger.info("update_ticket returned ticket with id=%s, title=%s", ticket.id, ticket.title)
        return {
            "success": True,
            "command": {"type": "update_ticket", "params": params},
            "result": format_ticket_for_json(ticket),
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "command": {"type": "update_ticket", "params": params},
            "result": None,
            "error": str(e),
        }


def _execute_delete_ticket(params: dict[str, Any], ticket_client: TicketInterface) -> dict[str, Any]:
    """Execute delete_ticket command.

    Args:
        params: Command parameters with "ticket_id".
        ticket_client: The ticket client interface.

    Returns:
        Result dictionary.

    """
    ticket_id = params.get("ticket_id")

    if not ticket_id:
        return {
            "success": False,
            "command": {"type": "delete_ticket", "params": params},
            "result": None,
            "error": "Missing required parameter: ticket_id",
        }

    try:
        logger.info("Calling ticket_client.delete_ticket(ticket_id=%s)", ticket_id)
        success = ticket_client.delete_ticket(str(ticket_id))
        logger.info("delete_ticket returned success=%s", success)
        if success:
            return {
                "success": True,
                "command": {"type": "delete_ticket", "params": params},
                "result": {"deleted": True, "ticket_id": str(ticket_id)},
                "error": None,
            }
        return {  # noqa: TRY300
            "success": False,
            "command": {"type": "delete_ticket", "params": params},
            "result": None,
            "error": f"Failed to delete ticket with ID '{ticket_id}'",
        }
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "command": {"type": "delete_ticket", "params": params},
            "result": None,
            "error": str(e),
        }
