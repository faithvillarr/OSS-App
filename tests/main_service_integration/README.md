# Main Service Integration Tests

Integration tests that verify component interactions **without hitting real external services**. All external APIs (Discord, Google Tasks, OpenAI) are mocked.

## Test Files (Organized by Data Flow)

### `test_discord_to_ai.py` - Discord → AI
Tests receiving Discord messages and processing with AI:
- Discord message receiving, filtering, and initialization
- Bot user ID determination
- AI command extraction from messages
- Chat client integration

### `test_ai_to_discord.py` - AI → Discord
Tests AI response generation and sending to Discord:
- AI response generation from ticket results
- Response formatting and validation
- Sending responses to Discord channels

### `test_ai_to_ticketing.py` - AI → Ticketing
Tests AI command extraction and ticketing execution:
- AI command extraction from user messages
- Command validation and correction
- Executing AI-extracted commands (create, search, update)

### `test_ticketing_to_ai.py` - Ticketing → AI
Tests ticketing operations and result formatting for AI:
- All ticket operations (create, get, search, update, delete)
- Result formatting from ticketing operations
- Passing ticket results to AI for response generation

## Running Tests

```bash
# Run all integration tests
uv run pytest tests/main_service_integration/ -v -m integration

# Run a specific flow
uv run pytest tests/main_service_integration/test_discord_to_ai.py -v
uv run pytest tests/main_service_integration/test_ai_to_discord.py -v
uv run pytest tests/main_service_integration/test_ai_to_ticketing.py -v
uv run pytest tests/main_service_integration/test_ticketing_to_ai.py -v
```

## Mock Strategy

All external services are mocked using `unittest.mock.MagicMock`:

- **AI Client**: `ai_api.get_client` is patched to return mock responses
- **Tickets Client**: `TicketsClient` methods return fake ticket objects
- **Discord Client**: `DiscordClient` methods simulate message operations

Fixtures are defined in `conftest.py` (`mock_discord_client`, `mock_tickets_client`) and in individual test files (`mock_ai_client`).

## Important Notes

- ✅ **No real API calls**: Tests run entirely in-memory
- ✅ **Fast execution**: No network requests
- ✅ **Component interactions**: Tests verify how components work together
- ⚠️ For end-to-end testing with real services, use separate "live" integration tests
