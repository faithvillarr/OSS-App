"""Chat endpoints implementing ChatInterface."""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from slack_sdk import WebClient as SlackWebClient
from slack_sdk.errors import SlackApiError

# MessageABC is abstract, we use our own Message model
from main_service.command_parser import CommandParser
from main_service.dependencies import require_authentication, require_bot_token
from main_service.tickets_integration import TicketsIntegration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_tickets_integration = TicketsIntegration()


class Message(BaseModel):
    """Message model for API responses."""

    id: str
    channel_id: str
    content: str
    sender_id: str = "system"
    timestamp: float | None = None


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""

    channel_id: str
    content: str
    sender_id: str = "user"


class MessageResponse(BaseModel):
    """Response model for a single message."""

    message: Message


class MessagesResponse(BaseModel):
    """Response model for a list of messages."""

    messages: list[Message]


@router.post("/messages", response_model=MessageResponse, status_code=201)
def send_message(
    request: SendMessageRequest,
    user_id: str = Depends(require_authentication),
    bot_token: str = Depends(require_bot_token),
) -> MessageResponse:
    """Send a message to a Slack channel.

    If the message contains a ticket command, it will be executed and the result
    will be returned as a response message.

    Args:
        request: The message request.
        user_id: Authenticated user ID (from dependency).
        bot_token: Bot token for Slack API (from dependency).

    Returns:
        The created message.

    Raises:
        HTTPException: 401 if not authenticated or bot token not found.
        HTTPException: 502 if Slack API call fails.

    """
    channel_id = request.channel_id
    content = request.content
    sender_id = request.sender_id

    logger.info(
        "Sending message to channel %s from user %s (sender_id=%s)",
        channel_id,
        user_id,
        sender_id,
    )

    # Initialize Slack client
    client = SlackWebClient(token=bot_token)

    # Check if message contains a ticket command
    if CommandParser.is_ticket_command(content):
        logger.info("Detected ticket command in message: %s", content)
        parsed = CommandParser.parse_command(content)
        if parsed:
            command_name, args = parsed
            success, response_message, data = _tickets_integration.execute_command(
                command_name, args
            )

            # Create response message with command result
            response_content = response_message
            if not success:
                response_content = f"Error: {response_message}"

            # Post original message to Slack
            try:
                original_resp = client.chat_postMessage(channel=channel_id, text=content)
                original_ts = original_resp.get("ts", "")
                original_msg_id = original_resp.get("message", {}).get("ts", original_ts)
            except SlackApiError as e:
                logger.error("Failed to post original message to Slack: %s", e)
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to post message to Slack: {e.response.get('error', 'unknown error')}",
                ) from e

            # Post response message to Slack
            try:
                response_resp = client.chat_postMessage(
                    channel=channel_id, text=response_content
                )
                response_ts = response_resp.get("ts", "")
                response_msg_id = response_resp.get("message", {}).get("ts", response_ts)
            except SlackApiError as e:
                logger.error("Failed to post response message to Slack: %s", e)
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to post response to Slack: {e.response.get('error', 'unknown error')}",
                ) from e

            return MessageResponse(
                message=Message(
                    id=response_msg_id,
                    channel_id=channel_id,
                    content=response_content,
                    sender_id="system",
                    timestamp=float(response_ts) if response_ts else time.time(),
                )
            )

    # Regular message (no command) - post to Slack
    try:
        resp = client.chat_postMessage(channel=channel_id, text=content)
        ts = resp.get("ts", "")
        msg_id = resp.get("message", {}).get("ts", ts)
        timestamp = float(ts) if ts else time.time()
    except SlackApiError as e:
        logger.error("Failed to post message to Slack: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to post message to Slack: {e.response.get('error', 'unknown error')}",
        ) from e

    return MessageResponse(
        message=Message(
            id=msg_id,
            channel_id=channel_id,
            content=content,
            sender_id=sender_id,
            timestamp=timestamp,
        )
    )


@router.get("/messages/{channel_id}", response_model=MessagesResponse)
def get_messages(
    channel_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    user_id: str = Depends(require_authentication),
    bot_token: str = Depends(require_bot_token),
) -> MessagesResponse:
    """Get messages from a Slack channel.

    This endpoint fetches messages directly from Slack using the Slack API.

    Args:
        channel_id: The Slack channel ID.
        limit: Maximum number of messages to return.
        user_id: Authenticated user ID (from dependency).
        bot_token: Bot token for Slack API (from dependency).

    Returns:
        List of messages from the Slack channel.

    Raises:
        HTTPException: 401 if not authenticated or bot token not found.
        HTTPException: 502 if Slack API call fails.

    """
    logger.info(
        "Getting messages for channel %s (limit=%d, user=%s)",
        channel_id,
        limit,
        user_id,
    )

    # Initialize Slack client
    client = SlackWebClient(token=bot_token)

    try:
        # Fetch messages from Slack
        resp = client.conversations_history(channel=channel_id, limit=limit)
        slack_messages = resp.get("messages", [])
    except SlackApiError as e:
        logger.error("Failed to fetch messages from Slack: %s", e)
        error_detail = e.response.get("error", "unknown error") if hasattr(e, "response") else str(e)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch messages from Slack: {error_detail}",
        ) from e

    # Convert Slack messages to our Message format
    messages = []
    for slack_msg in slack_messages:
        msg_text = slack_msg.get("text", "")
        msg_ts = slack_msg.get("ts", "")
        msg_user = slack_msg.get("user", "unknown")
        
        # Convert timestamp string to float
        timestamp = float(msg_ts) if msg_ts else None
        
        messages.append(
            Message(
                id=msg_ts,  # Use Slack timestamp as message ID
                channel_id=channel_id,
                content=msg_text,
                sender_id=msg_user,
                timestamp=timestamp,
            )
        )

    # Sort by timestamp (most recent first)
    messages.sort(key=lambda m: m.timestamp or 0, reverse=True)

    logger.info(
        "Returning %d messages from channel %s",
        len(messages),
        channel_id,
    )

    return MessagesResponse(messages=messages)


@router.delete("/messages/{message_id}", status_code=204)
def delete_message(
    message_id: str,
    channel_id: str = Query(..., description="Channel ID containing the message"),
    user_id: str = Depends(require_authentication),
    bot_token: str = Depends(require_bot_token),
) -> None:
    """Delete a message from Slack.

    Args:
        message_id: The message timestamp (ts) to delete.
        channel_id: The channel ID containing the message.
        user_id: Authenticated user ID (from dependency).
        bot_token: Bot token for Slack API (from dependency).

    Raises:
        HTTPException: 401 if not authenticated or bot token not found.
        HTTPException: 404 if message not found.
        HTTPException: 502 if Slack API call fails.

    """
    logger.info("Deleting message %s from channel %s by user %s", message_id, channel_id, user_id)

    # Initialize Slack client
    client = SlackWebClient(token=bot_token)

    try:
        # Delete message from Slack
        client.chat_delete(channel=channel_id, ts=message_id)
        logger.info("Successfully deleted message %s from channel %s", message_id, channel_id)
    except SlackApiError as e:
        error_detail = e.response.get("error", "unknown error") if hasattr(e, "response") else str(e)
        if error_detail == "message_not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Message {message_id} not found in channel {channel_id}",
            ) from e
        logger.error("Failed to delete message from Slack: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to delete message from Slack: {error_detail}",
        ) from e

