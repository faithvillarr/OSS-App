# Main Service Integration Tests

This directory contains integration tests for the main_service that verify component interactions without hitting real external services.

## Test Structure

### Files

- `conftest.py` - Shared fixtures for mocking external services (Discord, Google Tasks)
- `test_chat_tickets_integration.py` - Tests for chat router with tickets integration
- `test_tickets_router_integration.py` - Tests for tickets router endpoints
- `test_message_poller_integration.py` - Tests for message poller with tickets integration

## Key Principles

1. **No Real External Services**: All external APIs (Discord, Google Tasks) are mocked
2. **Component Interaction**: Tests verify how components work together
3. **Isolation**: Each test is isolated and doesn't affect others
4. **Fast Execution**: Tests run quickly without network calls

## Fixtures

### `mock_discord_client`
Creates a mock DiscordClient with common methods configured.

### `mock_tickets_client`
Creates a mock TicketsClient with default return values.

### `mock_tickets_integration`
Creates a mock TicketsIntegration that:
- Uses the mock_tickets_client internally
- Implements execute_command logic for all ticket commands
- Is automatically injected into chat.py and tickets.py routers

### `app_with_mocks`
Provides a TestClient instance with all external services mocked.

## Running Tests

```bash
# Run all integration tests
uv run pytest tests/main_service_integration/ -v -m integration

# Run specific test file
uv run pytest tests/main_service_integration/test_chat_tickets_integration.py -v

# Run with coverage
uv run pytest tests/main_service_integration/ --cov=main_service --cov-report=term-missing
```
