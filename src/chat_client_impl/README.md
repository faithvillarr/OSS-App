> ### Team 2 Wrapper for Team 7s Implementation/Misaligned API
>
> This is our teams wrapper for Team 7s discord implementation to make it align with the shared Chat API contract.  


# Chat Client Implementation

Chat API implementation that adapts `discord_api` (which uses `discord_client_impl`) to work with the minimal `chat_api` contract.

## Overview

This package provides an adapter layer that bridges between:
- **Input**: The richer `discord_api` interface (which internally uses `discord_client_impl`)
- **Output**: The minimal `chat_api` contract (`ChatInterface`, `Message`)

The adapter implements the `chat_api.ChatInterface` with three core methods:
- `send_message(channel_id, content) -> bool`
- `get_messages(channel_id, limit) -> list[Message]`
- `delete_message(channel_id, message_id) -> bool`

## Architecture

The adapter pattern allows code written against the minimal `chat_api` contract to work with Discord as the backend implementation, without needing to know about Discord-specific features like channels, guilds, or rich message metadata.

### Components

- **`ChatClient`**: Implements `chat_api.ChatInterface`, delegates to `discord_api.get_client()` or creates `DiscordClient` directly
- **`ChatMessage`**: Implements `chat_api.Message`, wraps `discord_api.Message` and exposes only the minimal properties (`id`, `content`, `sender_id`)

## Usage

### Direct Instantiation

```python
from chat_client_impl import ChatClient

# Create client with access token (like DiscordClient)
client = ChatClient(access_token="your_bot_token", token_type="Bot")

# Use the chat API interface
success = client.send_message(channel_id="123456", content="Hello, world!")
messages = client.get_messages(channel_id="123456", limit=10)
for msg in messages:
    print(f"[{msg.id}] {msg.content} (from {msg.sender_id})")

client.delete_message(channel_id="123456", message_id="789")
```

### Factory Pattern

```python
from chat_client_impl import ChatClient

# Create client using user_id (uses discord_api.get_client internally)
client = ChatClient(user_id="user123")

# Same interface
client.send_message(channel_id="123456", content="Hello!")
```

### Using the Factory Function

```python
from chat_client_impl import get_client

client = get_client(user_id="user123")
messages = client.get_messages(channel_id="123456", limit=5)
```

## Dependencies

- `chat-api`: The minimal chat interface contract
- `discord-api`: The Discord-specific API contract
- `discord-client-impl`: The Discord implementation (imported as side-effect to register with `discord_api`)

## How It Works

1. When `ChatClient` is instantiated, it imports `discord_client_impl` (which auto-registers with `discord_api`)
2. If `access_token` is provided, it creates a `DiscordClient` directly
3. Otherwise, it uses `discord_api.get_client(user_id)` to get a registered Discord client
4. All method calls delegate to the underlying Discord client
5. `ChatMessage` wraps `discord_api.Message` instances and exposes only the minimal `chat_api.Message` properties

## Error Handling

Exceptions from `discord_api` are propagated as-is. The `chat_api` contract doesn't define custom exceptions, so standard Python exceptions and Discord-specific exceptions may be raised.

## Example: Integration Test

See `discord_main.py` in the project root, which demonstrates using `chat_client_impl` instead of `discord_client_impl` directly, proving that the adapter correctly bridges the interfaces.
