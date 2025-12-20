"""AI-powered routing for ticket management commands."""

import json
import logging
from typing import TYPE_CHECKING, Any

import ai_api

if TYPE_CHECKING:
    from tickets_api import TicketInterface
import main_service.ticketing as ticketing_module
import openai_impl  # noqa: F401
from main_service.prompts import (
    get_command_extraction_prompt,
    get_error_correction_prompt,
    get_followup_command_prompt,
    get_response_generation_prompt,
)

logger = logging.getLogger(__name__)

# Command extraction schema for structured AI output
COMMAND_SCHEMA = {
    "name": "ticket_commands",
    "description": "Extract ticket management commands from user message",
    "schema": {
        "type": "object",
        "properties": {
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "create_ticket",
                                "get_ticket",
                                "search_tickets",
                                "update_ticket",
                                "delete_ticket",
                            ],
                        },
                        "params": {
                            "type": "object",
                            "properties": {
                                "ticket_id": {
                                    "type": ["string", "null"],
                                    "description": "The ID of the ticket (required for get_ticket, update_ticket, delete_ticket)"
                                },
                                "title": {
                                    "type": ["string", "null"],
                                    "description": (
                                        "The title of the ticket "
                                        "(required for create_ticket, optional for update_ticket)"
                                    )
                                },
                                "description": {
                                    "type": ["string", "null"],
                                    "description": "The description of the ticket (required for create_ticket)"
                                },
                                "status": {
                                    "type": ["string", "null"],
                                    "enum": ["open", "in_progress", "closed"],
                                    "description": "The status of the ticket (optional for search_tickets and update_ticket)"
                                },
                                "query": {
                                    "type": ["string", "null"],
                                    "description": (
                                        "Search query to filter tickets by title/description "
                                        "(optional for search_tickets)"
                                    )
                                },
                                "assignee": {
                                    "type": ["string", "null"],
                                    "description": "The assignee of the ticket (optional for create_ticket)"
                                }
                            },
                            "required": ["ticket_id", "title", "description", "status", "query", "assignee"],
                            "additionalProperties": False,  # Required by OpenAI's structured output format
                            # Note: All possible parameters are defined above
                            # OpenAI requires all properties to be in 'required', but actual validation
                            # of which fields are required for which command types is handled by
                            # our _validate_command_response function
                        },
                    },
                    "required": ["type", "params"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["actions"],
        "additionalProperties": False,
    },
}


def extract_commands(user_message: str) -> list[dict[str, Any]]:
    """Extract ticket commands from a user message using AI.

    Includes validation and retry logic to handle invalid AI responses.

    Args:
        user_message: The user's message text.

    Returns:
        List of command dictionaries, each with "type" and "params" keys.
        Returns empty list if no commands are found or on error.

    """
    ai_client = ai_api.get_client()
    system_prompt = get_command_extraction_prompt()
    max_retries = 3
    validation_errors: list[str] = []

    for attempt in range(max_retries):
        try:
            # Build user input with validation errors if this is a retry
            user_input = user_message
            if validation_errors:
                error_feedback = "\n\n".join([
                    f"Previous attempt {i+1} failed: {error}"
                    for i, error in enumerate(validation_errors)
                ])
                user_input = f"""{user_message}

IMPORTANT: The previous response had validation errors. Please fix them:
{error_feedback}

Required format:
- Response must be a JSON object with an "actions" array
- Each action must have "type" (one of: create_ticket, get_ticket, search_tickets, update_ticket, delete_ticket)
- Each action must have "params" (a JSON object with the parameters)
- Ensure all required fields are present and correctly formatted"""

            logger.debug("Extracting commands (attempt %d/%d)", attempt + 1, max_retries)

            response = ai_client.generate_response(
                user_input=user_input,
                system_prompt=system_prompt,
                response_schema=COMMAND_SCHEMA,
            )

            # Validate the response
            is_valid, error_msg = _validate_command_response(response)

            if is_valid:
                actions = response.get("actions", [])
                if attempt > 0:
                    logger.info("Successfully extracted %d command(s) after %d retry attempt(s)",
                              len(actions), attempt)
                else:
                    logger.info("Extracted %d command(s) from user message", len(actions))

                # Log each extracted command with details
                for i, action in enumerate(actions, 1):
                    logger.info("Extracted command %d: type=%s, params=%s",
                              i, action.get("type"), action.get("params", {}))

                return list(actions)  # type: ignore[no-any-return]

            # Validation failed - store error for retry
            validation_errors.append(error_msg or "Unknown validation error")
            logger.warning("Command extraction validation failed (attempt %d/%d): %s",
                         attempt + 1, max_retries, error_msg)

            # If this was the last attempt, log and return empty
            if attempt == max_retries - 1:
                logger.error("Failed to extract valid commands after %d attempts. Errors: %s",
                           max_retries, validation_errors)
                return []

        except Exception:
            logger.exception("Failed to extract commands from user message (attempt %d/%d)",
                           attempt + 1, max_retries)
            # If this was the last attempt, return empty
            if attempt == max_retries - 1:
                return []
            # Otherwise, continue to next retry
            continue

    # Should not reach here, but return empty as fallback
    return []


def generate_response(
    user_message: str, ticket_results: list[dict[str, Any]]
) -> str:
    """Generate a natural language response from ticket operation results.

    Args:
        user_message: The original user message.
        ticket_results: List of ticket operation results, each containing:
            - "success": bool
            - "command": dict (the original command)
            - "result": dict | None (ticket data if successful)
            - "error": str | None (error message if failed)

    Returns:
        Natural language response string.

    """
    try:
        ai_client = ai_api.get_client()
        system_prompt = get_response_generation_prompt()

        # Format ticket results for AI
        results_summary = _format_results_for_ai(ticket_results)

        user_input = f"""User message: {user_message}

Ticket operation results:
{results_summary}

Generate a helpful response to the user."""

        response = ai_client.generate_response(
            user_input=user_input,
            system_prompt=system_prompt,
            response_schema=None,  # Natural language response
        )

        if isinstance(response, str):
            return response
        logger.warning("AI returned non-string response for message generation")
        return "I processed your request, but I'm having trouble generating a response."  # noqa: TRY300
    except Exception:
        logger.exception("Failed to generate response")
        return "I encountered an error while processing your request. Please try again."


def correct_commands(
    original_commands: list[dict[str, Any]], error_message: str
) -> list[dict[str, Any]]:
    """Correct failed commands based on error messages using AI.

    Includes validation and retry logic to handle invalid AI responses.

    Args:
        original_commands: The commands that failed.
        error_message: The error message from the failed operation.

    Returns:
        List of corrected command dictionaries. Returns original_commands if all retries fail.

    """
    ai_client = ai_api.get_client()
    system_prompt = get_error_correction_prompt()
    max_retries = 3
    validation_errors: list[str] = []

    base_user_input = f"""Original commands that failed:
{_format_commands_for_ai(original_commands)}

Error message:
{error_message}

Please provide corrected commands."""

    for attempt in range(max_retries):
        try:
            # Build user input with validation errors if this is a retry
            user_input = base_user_input
            if validation_errors:
                error_feedback = "\n\n".join([
                    f"Previous attempt {i+1} failed: {error}"
                    for i, error in enumerate(validation_errors)
                ])
                user_input = f"""{base_user_input}

IMPORTANT: The previous correction attempt had validation errors. Please fix them:
{error_feedback}

Required format:
- Response must be a JSON object with an "actions" array
- Each action must have "type" (one of: create_ticket, get_ticket, search_tickets, update_ticket, delete_ticket)
- Each action must have "params" (a JSON object with the parameters)
- Ensure all required fields are present and correctly formatted"""

            logger.debug("Correcting commands (attempt %d/%d)", attempt + 1, max_retries)

            response = ai_client.generate_response(
                user_input=user_input,
                system_prompt=system_prompt,
                response_schema=COMMAND_SCHEMA,
            )

            # Validate the response
            is_valid, error_msg = _validate_command_response(response)

            if is_valid:
                actions = response.get("actions", [])
                if attempt > 0:
                    logger.info("Successfully corrected %d command(s) after %d retry attempt(s)",
                              len(actions), attempt)
                else:
                    logger.info("AI corrected %d command(s)", len(actions))

                # Log each corrected command with details
                for i, action in enumerate(actions, 1):
                    logger.info("Corrected command %d: type=%s, params=%s",
                              i, action.get("type"), action.get("params", {}))

                return list(actions)  # type: ignore[no-any-return]

            # Validation failed - store error for retry
            validation_errors.append(error_msg or "Unknown validation error")
            logger.warning("Command correction validation failed (attempt %d/%d): %s",
                         attempt + 1, max_retries, error_msg)

            # If this was the last attempt, log and return original
            if attempt == max_retries - 1:
                logger.error("Failed to correct commands after %d attempts. Errors: %s. Returning original commands.",
                           max_retries, validation_errors)
                return original_commands  # Return original if correction fails

        except Exception:
            logger.exception("Failed to correct commands (attempt %d/%d)",
                           attempt + 1, max_retries)
            # If this was the last attempt, return original
            if attempt == max_retries - 1:
                return original_commands  # Return original if correction fails
            # Otherwise, continue to next retry
            continue

    # Should not reach here, but return original as fallback
    return original_commands


def execute_commands_iteratively(  # noqa: C901, PLR0912, PLR0915
    user_message: str,
    initial_commands: list[dict[str, Any]],
    ticket_client: "TicketInterface",
    max_iterations: int = 5,
) -> list[dict[str, Any]]:
    """Execute commands iteratively, passing results back to AI for follow-up commands.

    Commands are executed one at a time. After each execution, results are passed
    back to the AI to generate the next command(s) based on previous results.

    Args:
        user_message: The original user message.
        initial_commands: Initial commands to execute (from initial AI extraction).
        ticket_client: The ticket client interface for executing commands.
        max_iterations: Maximum number of AI-ticketing interaction rounds (default: 5).

    Returns:
        List of all accumulated result dictionaries from all executed commands.

    """
    all_results: list[dict[str, Any]] = []
    pending_commands = initial_commands.copy()
    iteration = 0

    logger.info("Starting iterative command execution with %d initial command(s), max %d iterations",
                len(initial_commands), max_iterations)

    while pending_commands and iteration < max_iterations:
        iteration += 1
        logger.info("=== Iteration %d/%d ===", iteration, max_iterations)

        # Execute the first pending command
        current_command = pending_commands[0]
        pending_commands = pending_commands[1:]

        logger.info("Executing command: type=%s, params=%s",
                   current_command.get("type"), current_command.get("params", {}))

        # Execute the command
        command_results = ticketing_module.execute_commands([current_command], ticket_client)
        result = command_results[0] if command_results else None

        if result:
            all_results.append(result)

            if result.get("success"):
                logger.info("Command succeeded in iteration %d", iteration)
            else:
                logger.warning("Command failed in iteration %d: %s",
                             iteration, result.get("error", "Unknown error"))

        # After each command execution, ask AI for follow-up commands
        # This allows the AI to use results from previous commands to generate next commands
        if iteration < max_iterations:
            # Format all results so far for AI
            results_summary = _format_results_for_ai(all_results)

            # Log the raw JSON results being passed to AI (for debugging)
            logger.debug("Results being passed to AI (iteration %d): %s",
                        iteration, _format_results_as_json(all_results))

            # Determine context message
            context_message = ""
            if pending_commands:
                context_message = (
                    f"There are {len(pending_commands)} more command(s) from the initial batch "
                    "waiting to be executed. However, you may need to generate follow-up commands "
                    "that use data from the results above. If a pending command needs data from "
                    "previous results, you can generate a new command with that data instead."
                )
            else:
                context_message = (
                    "All initial commands have been executed. Determine if the user's request "
                    "is complete or if follow-up commands are needed based on the results above."
                )

            user_input = f"""Original user message: {user_message}

Previous command results:
{results_summary}

{context_message}

CRITICAL INSTRUCTIONS FOR EXTRACTING TICKET_ID:

If you need to generate an update_ticket, delete_ticket, or get_ticket command:

STEP 1: Look at the "Raw JSON Results" section above
STEP 2: Find any search_tickets results - they will have result.tickets[] array
STEP 3: MATCH THE TICKET BY TITLE:
   - Extract keywords from the user's message (e.g., "cloud components" from "mark my cloud components task")
   - Look through each ticket in result.tickets[] array
   - Compare each ticket's "title" field with the keywords (case-insensitive, partial match)
   - Find the ticket whose title best matches the user's description
STEP 4: Extract the "id" field from the matched ticket
STEP 5: Use that exact id value as the "ticket_id" parameter in your command

EXAMPLE:
- User message: "mark my cloud components task as in progress"
- Search results show tickets: [
    {{"id": "abc123", "title": "Cloud Components", ...}},
    {{"id": "def456", "title": "Other Task", ...}}
  ]
- Match: "Cloud Components" matches "cloud components" → ticket_id = "abc123"
- Generate: {{"type": "update_ticket", "params": {{"ticket_id": "abc123", "status": "in_progress"}}}}

ABSOLUTE REQUIREMENTS:
- NEVER generate update_ticket/delete_ticket/get_ticket without ticket_id parameter
- If you cannot find a matching ticket_id in the JSON results, return an empty actions array []
- You MUST parse the JSON structure to extract ticket_id - do not guess or leave it empty
- For search_tickets results: ticket_id is in results[].result.tickets[].id (after matching by title)
- For single ticket results: ticket_id is in results[].result.id

If the request is fully satisfied, return an empty actions array []"""

            ai_client = ai_api.get_client()
            system_prompt = get_followup_command_prompt()

            try:
                logger.info("Asking AI for follow-up commands (iteration %d, %d pending)",
                          iteration, len(pending_commands))
                response = ai_client.generate_response(
                    user_input=user_input,
                    system_prompt=system_prompt,
                    response_schema=COMMAND_SCHEMA,
                )

                # Validate the response
                is_valid, error_msg = _validate_command_response(response)

                if is_valid:
                    followup_commands = response.get("actions", [])
                    if followup_commands:
                        logger.info("AI generated %d follow-up command(s) in iteration %d",
                                  len(followup_commands), iteration)
                        # Add follow-up commands to pending queue (they'll be executed next)
                        # We prepend them so they execute before remaining initial commands
                        # This allows follow-ups that depend on results to execute immediately
                        pending_commands = followup_commands + pending_commands
                    else:
                        logger.info("AI determined no more commands needed (iteration %d)", iteration)
                        # If no follow-ups and no pending commands, we're done
                        if not pending_commands:
                            break
                else:
                    logger.warning("AI follow-up response validation failed (iteration %d): %s",
                                 iteration, error_msg)
                    # Continue with any remaining pending commands
                    if not pending_commands:
                        break
            except Exception:
                logger.exception("Error generating follow-up commands (iteration %d)", iteration)
                # Continue with any remaining pending commands
                if not pending_commands:
                    break

    if iteration >= max_iterations:
        logger.warning("Reached maximum iterations (%d). Some commands may not have been executed.",
                     max_iterations)
        if pending_commands:
            logger.warning("Remaining pending commands: %d", len(pending_commands))

    logger.info("Iterative execution complete: %d iteration(s), %d total result(s)",
                iteration, len(all_results))

    return all_results


def _format_results_as_json(results: list[dict[str, Any]]) -> str:
    """Format results as raw JSON string for AI parsing.

    Args:
        results: List of result dictionaries.

    Returns:
        JSON string representation of results.

    """
    return json.dumps(results, indent=2)


def _format_results_for_ai(results: list[dict[str, Any]]) -> str:
    """Format ticket operation results for AI processing.

    Provides both formatted text summary (human-readable) and raw JSON structure
    (machine-parseable) to enable reliable data extraction.

    Args:
        results: List of result dictionaries.

    Returns:
        Formatted string with both summary and JSON structure.

    """
    lines = []
    lines.append("=== Results Summary ===")
    for i, result in enumerate(results, 1):
        lines.append(f"Operation {i}:")
        command = result.get("command", {})
        command_type = command.get("type", "unknown")
        lines.append(f"  Command Type: {command_type}")
        lines.append(f"  Command Params: {command.get('params', {})}")

        if result.get("success"):
            ticket_data = result.get("result")
            if ticket_data:
                lines.append("  Success: True")

                # Highlight ticket_id if present (critical for follow-up commands)
                if isinstance(ticket_data, dict):
                    if "id" in ticket_data:
                        lines.append(f"  *** TICKET_ID: {ticket_data['id']} *** (use this for update/delete/get operations)")
                    if "tickets" in ticket_data:
                        # This is a search result
                        tickets = ticket_data.get("tickets", [])
                        lines.append(f"  Found {len(tickets)} ticket(s):")
                        for j, ticket in enumerate(tickets, 1):
                            if isinstance(ticket, dict) and "id" in ticket:
                                ticket_id = ticket["id"]
                                ticket_title = ticket.get("title", "N/A")
                                ticket_status = ticket.get("status", "N/A")
                                lines.append(f"    Ticket {j}:")
                                lines.append(f"      TITLE: \"{ticket_title}\" (match this with user's message)")
                                lines.append(f"      ID: {ticket_id}")
                                lines.append(f"      STATUS: {ticket_status}")
                                lines.append(f"      *** USE TICKET_ID: {ticket_id} for update/delete/get operations ***")
                    else:
                        # Single ticket result - show all fields
                        lines.append(f"  Ticket Data: {ticket_data}")
                else:
                    lines.append(f"  Result: {ticket_data}")
            else:
                lines.append("  Success: True (no data returned)")
        else:
            lines.append("  Success: False")
            lines.append(f"  Error: {result.get('error', 'Unknown error')}")
        lines.append("")

    lines.append("\n=== Raw JSON Results (Parse this for data extraction) ===")
    lines.append("CRITICAL: Parse the JSON structure below to extract ticket_id and other required data.")
    lines.append("The JSON structure is:")
    lines.append(_format_results_as_json(results))

    return "\n".join(lines)


def _format_commands_for_ai(commands: list[dict[str, Any]]) -> str:
    """Format commands for AI processing.

    Args:
        commands: List of command dictionaries.

    Returns:
        Formatted string representation of commands.

    """
    return json.dumps(commands, indent=2)


def _validate_command_response(response: object) -> tuple[bool, str | None]:  # noqa: C901, PLR0911
    """Validate the AI-generated command response.

    Checks that the response has the correct structure:
    - Response is a dict
    - Has "actions" key (list)
    - Each action has "type" and "params" keys
    - "type" is one of the valid enum values
    - "params" is a dict

    Args:
        response: The response from the AI to validate.

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.

    """
    # Check if response is a dict
    if not isinstance(response, dict):
        return False, f"Response is not a dict, got {type(response).__name__}"

    # Check for "actions" key
    if "actions" not in response:
        return False, "Response missing 'actions' key"

    actions = response["actions"]

    # Check if actions is a list
    if not isinstance(actions, list):
        return False, f"'actions' is not a list, got {type(actions).__name__}"

    # Valid command types
    valid_types = {
        "create_ticket",
        "get_ticket",
        "search_tickets",
        "update_ticket",
        "delete_ticket",
    }

    # Validate each action
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            return False, f"Action {i} is not a dict, got {type(action).__name__}"

        # Check for "type" key
        if "type" not in action:
            return False, f"Action {i} missing 'type' key"

        action_type = action["type"]
        if not isinstance(action_type, str):
            return False, f"Action {i} 'type' is not a string, got {type(action_type).__name__}"

        if action_type not in valid_types:
            return False, f"Action {i} has invalid 'type': '{action_type}'. Must be one of {valid_types}"

        # Check for "params" key
        if "params" not in action:
            return False, f"Action {i} missing 'params' key"

        params = action["params"]
        if not isinstance(params, dict):
            return False, f"Action {i} 'params' is not a dict, got {type(params).__name__}"

    return True, None
