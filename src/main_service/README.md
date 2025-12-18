# Chat Service

FastAPI service that provides chat functionality with integrated ticket operations via command parsing.

## Overview

This service implements the `chat_api.ChatInterface` and allows users to interact with tickets through natural chat commands. When a message contains a ticket command (e.g., `get_tickets(bug, open)`), the service automatically executes the command and returns the result.

## Features

- Chat endpoints: send, get, and delete messages
- Ticket command parsing from chat messages
- Direct ticket command execution endpoint
- Integration with `tickets_client_impl` for Google Tasks backend

## API Endpoints

### Authentication Endpoints

- `GET /auth/login` - Redirect to Slack OAuth login page
- `GET /auth/callback` - OAuth callback handler (called by Slack)
- `GET /auth/status` - Check authentication status
- `POST /auth/logout` - Log out and clear session

### Chat Endpoints

- `POST /chat/messages` - Send a message (with automatic command parsing)
- `GET /chat/messages/{channel_id}` - Get messages from a channel
- `DELETE /chat/messages/{message_id}` - Delete a message

### Ticket Endpoints

- `POST /tickets/execute` - Execute a ticket command directly

### Infrastructure

- `GET /health` - Health check
- `GET /` - Service information

## Command Format

Commands are parsed from messages using the format: `command_name(arg1, arg2, ...)`

### Supported Commands

- `get_tickets(query?, status?)` - Search for tickets
  - Example: `get_tickets(bug, open)`
- `create_ticket(title, description)` - Create a new ticket
  - Example: `create_ticket("Fix login", "Users cannot authenticate")`
- `get_ticket(ticket_id)` - Get a specific ticket
  - Example: `get_ticket(abc123)`
- `update_ticket(ticket_id, status?, title?)` - Update a ticket
  - Example: `update_ticket(abc123, in_progress, "Fix login (updated)")`
- `delete_ticket(ticket_id)` - Delete a ticket
  - Example: `delete_ticket(abc123)`

## Environment Variables

### Required for Ticket Operations
- `TASKS_CLIENT_ID` - Google OAuth client ID
- `TASKS_CLIENT_SECRET` - Google OAuth client secret
- `TASKS_REFRESH_TOKEN` - Google OAuth refresh token

### Required for Slack OAuth Authentication
- `OAUTH_CLIENT_ID` - Slack OAuth client ID
- `OAUTH_CLIENT_SECRET` - Slack OAuth client secret
- `OAUTH_REDIRECT_URI` - Slack OAuth redirect URI (e.g., `http://localhost:8080/auth/callback`)

### Optional
- `SESSION_SECRET` - Session secret for FastAPI middleware (default: dev-secret-key-change-in-production)
- `DATABASE_URL` - SQLite database path for token storage (default: `sqlite:///./var/chat_tokens.db`)

## Running Locally

```bash
# Install dependencies (including slack_impl)
uv sync --all-packages
python -m pip install -e ../slack_impl

# Set up environment variables (create a .env file or export them)
export OAUTH_CLIENT_ID="your-slack-client-id"
export OAUTH_CLIENT_SECRET="your-slack-client-secret"
export OAUTH_REDIRECT_URI="http://localhost:8080/auth/callback"

# Run the service
uv run uvicorn main_service.app:app --reload --port 8080
```

## Authentication

The service uses Slack OAuth for authentication. To authenticate:

1. **Visit the login endpoint**: Open `http://localhost:8080/auth/login` in your browser
2. **Authorize with Slack**: You'll be redirected to Slack's OAuth page
3. **Grant permissions**: Authorize the app to access your Slack workspace
4. **Return to service**: After authorization, you'll be redirected back to `/docs`

Alternatively, you can check your authentication status:
```bash
curl http://localhost:8080/auth/status
```

**Note**: Make sure to configure your Slack app's OAuth redirect URI to match `OAUTH_REDIRECT_URI` (e.g., `http://localhost:8080/auth/callback`).

## Usage Example

Send a message with a ticket command:

```bash
curl -X POST http://localhost:8080/chat/messages \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "channel1",
    "content": "get_tickets(bug, open)"
  }'
```

The service will automatically detect the command, execute it, and return the results as a response message.

