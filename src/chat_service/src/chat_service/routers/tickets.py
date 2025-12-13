"""Ticket command endpoints (alternative to chat message parsing)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from chat_service.command_parser import CommandParser
from chat_service.tickets_integration import TicketsIntegration

router = APIRouter(prefix="/tickets", tags=["tickets"])

_tickets_integration = TicketsIntegration()


class CommandRequest(BaseModel):
    """Request model for executing a ticket command."""

    command: str
    args: list[str] = []


class CommandResponse(BaseModel):
    """Response model for command execution."""

    success: bool
    message: str
    data: dict | list | None = None


@router.post("/execute", response_model=CommandResponse)
def execute_command(request: CommandRequest) -> CommandResponse:
    """Execute a ticket command directly.

    This endpoint allows direct execution of ticket commands without
    going through the chat message parsing.

    Args:
        request: The command request.

    Returns:
        Command execution result.

    """
    command_name = request.command.lower()
    args = request.args

    if command_name not in {
        "get_tickets",
        "create_ticket",
        "get_ticket",
        "update_ticket",
        "delete_ticket",
    }:
        raise HTTPException(
            status_code=400, detail=f"Unknown command: {command_name}"
        )

    success, message, data = _tickets_integration.execute_command(command_name, args)

    # Convert ticket objects to dicts for JSON serialization
    response_data = None
    if data is not None:
        if isinstance(data, list):
            response_data = [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status.value,
                    "assignee": t.assignee,
                }
                if hasattr(t, "id")
                else t
                for t in data
            ]
        elif hasattr(data, "id"):
            # Single ticket object
            response_data = {
                "id": data.id,
                "title": data.title,
                "description": data.description,
                "status": data.status.value,
                "assignee": data.assignee,
            }
        else:
            response_data = data

    return CommandResponse(success=success, message=message, data=response_data)

