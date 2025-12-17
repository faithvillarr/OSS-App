"""Command parser for ticket operations in chat messages."""

import re
from typing import Any

import gtask_client_impl  # noqa: F401
from tickets_api import TicketStatus


class CommandParser:
    """Parses ticket commands from chat messages."""

    # Pattern to match command_name(arg1, arg2, ...)
    # Supports quoted strings and unquoted arguments
    COMMAND_PATTERN = re.compile(r"(\w+)\s*\((.*)\)\s*$", re.IGNORECASE)

    @staticmethod
    def parse_args(args_str: str) -> list[str]:
        """Parse arguments from a command string.

        Handles both quoted strings and unquoted arguments.
        Example: 'arg1, "arg2 with spaces", arg3' -> ['arg1', 'arg2 with spaces', 'arg3']

        Args:
            args_str: The arguments string to parse.

        Returns:
            List of parsed arguments.

        """
        if not args_str.strip():
            return []

        args: list[str] = []
        current_arg = ""
        in_quotes = False
        quote_char = None

        i = 0
        while i < len(args_str):
            char = args_str[i]

            if char in ('"', "'") and (i == 0 or args_str[i - 1] != "\\"):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
                else:
                    current_arg += char
            elif char == "," and not in_quotes:
                if current_arg.strip():
                    args.append(current_arg.strip())
                current_arg = ""
            else:
                current_arg += char

            i += 1

        if current_arg.strip():
            args.append(current_arg.strip())

        return args

    @staticmethod
    def parse_command(message: str) -> tuple[str, list[str]] | None:
        match = CommandParser.COMMAND_PATTERN.search(message)
        if not match:
            return None

        command_name = match.group(1).lower()
        args_str = match.group(2)

        try:
            args = CommandParser.parse_args(args_str)
        except ValueError:
            return None

        return command_name, args

    @staticmethod
    def is_ticket_command(message: str) -> bool:
        """Check if a message contains a ticket command.

        Args:
            message: The message text to check.

        Returns:
            True if the message contains a ticket command, False otherwise.

        """
        parsed = CommandParser.parse_command(message)
        if not parsed:
            return False

        command_name, _ = parsed
        ticket_commands = {
            "get_tickets",
            "create_ticket",
            "get_ticket",
            "update_ticket",
            "delete_ticket",
        }
        return command_name in ticket_commands

    @staticmethod
    def parse_status(status_str: str | None) -> TicketStatus | None:
        """Parse a status string to TicketStatus enum.

        Args:
            status_str: The status string to parse.

        Returns:
            TicketStatus enum value or None if invalid.

        """
        if not status_str:
            return None

        status_lower = status_str.lower().strip()
        status_map = {
            "open": TicketStatus.OPEN,
            "in_progress": TicketStatus.IN_PROGRESS,
            "inprogress": TicketStatus.IN_PROGRESS,
            "closed": TicketStatus.CLOSED,
        }
        return status_map.get(status_lower)

