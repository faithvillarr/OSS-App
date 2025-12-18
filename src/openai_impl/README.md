# OpenAI Implementation

## Overview
`openai_impl` provides a concrete implementation of `ai_api.AIInterface` backed by the OpenAI API. It handles API authentication and provides methods to generate both conversational and structured responses from OpenAI's language models.

## Purpose

This package serves as the production-ready OpenAI integration for the AI assistant system:

- **OpenAI API Integration**: Connects to OpenAI using the official Python client
- **API Key Authentication**: Handles secure authentication via API keys
- **ABC Implementation**: Provides concrete implementation of AIInterface
- **Structured Output Support**: Supports both conversational and structured responses using JSON Schema
- **Dependency Injection**: Automatically registers itself as the AIInterface implementation
- **Intent Detection**: Perfect for analyzing user input and extracting structured data

## Installation

This package is part of the `uv` workspace:

```bash
uv sync --all-packages
```

## Architecture

```
Consumer Code
    ↓
ai_api.get_client()
    ↓
openai_impl.OpenAIClient
    ↓
OpenAI API (gpt-4o-mini)
```

### Authentication
- API key authentication via environment variable `OPENAI_API_KEY`
- Credentials loaded automatically from environment
- Fails fast with clear error message if API key is missing

### Dependency Injection
```python
import openai_impl  # Auto-registers the implementation

from ai_api import get_client
client = get_client()  # Returns OpenAIClient instance
```

## API Reference

### OpenAIClient

Implements the `ai_api.AIInterface` abstract base class.

#### Constructor

```python
OpenAIClient(api_key: str | None = None, model: str | None = None)
```

**Parameters:**
- `api_key`: Optional API key. If not provided, reads from `OPENAI_API_KEY` env var
- `model`: Optional model name. Defaults to `gpt-4o-mini`

**Raises:**
- `RuntimeError`: If no API key is found or authentication fails

#### Methods

```python
def generate_response(
    user_input: str,
    system_prompt: str,
    response_schema: dict[str, Any] | None = None,
) -> str | dict[str, Any]:
    """Generate a response from OpenAI's API.
    
    Args:
        user_input: The text provided by the user
        system_prompt: Instructional system prompt
        response_schema: Optional JSON schema for structured output
        
    Returns:
        str: Conversational response (when response_schema is None)
        dict: Structured data matching schema (when response_schema is provided)
        
    Raises:
        RuntimeError: If the API call fails
    """
```

### Factory Functions

```python
def get_client_impl(api_key: str | None = None) -> AIInterface:
    """Return a configured OpenAIClient instance."""

def register(api_key: str | None = None) -> None:
    """Register the OpenAI client implementation with the AI API."""
```

## Usage Examples

### Basic Conversational Usage

```python
import openai_impl
from ai_api import get_client

# Implementation is automatically registered on import
client = get_client()

# Simple conversational response
response = client.generate_response(
    user_input="What is 2+2?",
    system_prompt="You are a helpful math tutor."
)
print(response)  # "2+2 equals 4."
```

### Direct Client Usage

```python
import openai_impl

# Create client directly
client = openai_impl.OpenAIClient()

response = client.generate_response(
    user_input="Explain Python decorators in one sentence.",
    system_prompt="You are concise and clear."
)
print(response)
```

### Structured Output for Intent Detection

The OpenAI implementation supports structured outputs using JSON Schema, perfect for analyzing user input and extracting structured data:

```python
import openai_impl
from ai_api import get_client

client = get_client()

# Define a schema for email action intent detection
email_action_schema = {
    "name": "email_action",
    "description": "Extract email action intent and parameters from user input",
    "schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["delete", "mark_as_read", "get_message", "list_messages"],
                "description": "The email action the user wants to perform"
            },
            "message_id": {
                "type": "string",
                "description": "The ID of the message to act upon (if applicable)"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of messages to retrieve (for list_messages)"
            }
        },
        "required": ["action"],
        "additionalProperties": False
    }
}

# User says: "Delete the email with ID 12345"
response = client.generate_response(
    user_input="Delete the email with ID 12345",
    system_prompt="You are an AI that extracts email action intents from user requests.",
    response_schema=email_action_schema
)

print(response)
# Output: {"action": "delete", "message_id": "12345"}
```

### Multi-Intent Detection

```python
from ai_api import get_client

client = get_client()

# Schema for detecting multiple possible actions
multi_action_schema = {
    "name": "intent_detection",
    "description": "Detect user intent and extract relevant parameters",
    "schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["email_management", "weather_query", "calendar_event", "general_conversation"]
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score between 0 and 1"
            },
            "parameters": {
                "type": "object",
                "description": "Intent-specific parameters",
                "additionalProperties": True
            }
        },
        "required": ["intent", "confidence"],
        "additionalProperties": False
    }
}

response = client.generate_response(
    user_input="Show me my last 5 unread emails",
    system_prompt="Analyze the user's intent and extract relevant parameters.",
    response_schema=multi_action_schema
)

print(response)
# Output: {
#   "intent": "email_management",
#   "confidence": 0.95,
#   "parameters": {
#     "action": "list_messages",
#     "filter": "unread",
#     "count": 5
#   }
# }
```

### Ticket Creation Example

```python
from ai_api import get_client

client = get_client()

ticket_schema = {
    "name": "ticket_command",
    "description": "Extract intent and title from a ticket request",
    "schema": {
        "type": "object",
        "properties": {
            "intent": {"type": "string"},
            "title": {"type": "string"},
        },
        "required": ["intent", "title"],
        "additionalProperties": False,
    },
}

result = client.generate_response(
    user_input="Create a ticket to fix login redirect.",
    system_prompt="Extract intent and title fields.",
    response_schema=ticket_schema,
)
print(result)
# Output: {"intent": "create_ticket", "title": "Fix login redirect"}
```

## Authentication Setup

### Environment Variables

```bash
export OPENAI_API_KEY="your_api_key_here"
```

### .env File

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_api_key_here
```

### Programmatic Configuration

```python
import openai_impl

# Pass API key directly
client = openai_impl.OpenAIClient(api_key="your_api_key_here")

# Or register with custom key
openai_impl.register(api_key="your_api_key_here")
```

## Configuration

### Model Selection

```python
import openai_impl

# Use default model (gpt-4o-mini)
client = openai_impl.OpenAIClient()

# Use custom model
client = openai_impl.OpenAIClient(model="gpt-4")
```

### Error Handling

```python
import openai_impl
from ai_api import get_client

try:
    client = get_client()
    response = client.generate_response("Hello", "Be helpful")
except RuntimeError as e:
    print(f"Error: {e}")
```

## Testing

```bash
# Run unit tests
uv run pytest src/openai_impl/tests/ -v

# Run with coverage
uv run pytest src/openai_impl/tests/ --cov=src/openai_impl --cov-report=term-missing

# Run specific test
uv run pytest src/openai_impl/tests/test_openai_impl.py::test_generate_response -v
```

## Response Schema Format

The `response_schema` parameter should follow this structure:

```python
{
    "name": "schema_name",           # Name of the schema
    "description": "What it does",   # Description
    "schema": {                      # JSON Schema specification
        "type": "object",
        "properties": {
            "field1": {"type": "string"},
            "field2": {"type": "integer"}
        },
        "required": ["field1"],
        "additionalProperties": False  # Recommended for strict mode
    }
}
```

## Integration with Other Components

- **ai_api**: Implements the `AIInterface` contract
- **ai_service**: Uses this implementation to process requests
- **ai_adapter**: Alternative implementation that calls the service remotely
- **main.py**: Demo script showing usage examples

## Design Patterns

1. **Abstract Base Class (ABC)**: Implements the `AIInterface` contract
2. **Dependency Injection**: Registers itself via `register()` function
3. **Factory Pattern**: Provides `get_client_impl()` factory function
4. **Fail Fast**: Clear error messages for missing configuration

## Performance Considerations

- **Model Selection**: `gpt-4o-mini` is fast and cost-effective for most use cases
- **Structured Output**: Uses OpenAI's native structured output mode for reliability
- **Strict Mode**: Enables strict JSON schema validation for guaranteed conformance
- **Error Handling**: Comprehensive error handling with clear messages

## Security Best Practices

- Never commit API keys to version control
- Use environment variables or secrets management
- Rotate API keys regularly
- Monitor API usage and set spending limits
- Use `.gitignore` to exclude `.env` files

## Troubleshooting

### "No OpenAI API key found"

```bash
# Set the environment variable
export OPENAI_API_KEY="your_key_here"

# Or create a .env file
echo "OPENAI_API_KEY=your_key_here" > .env
```

### "Failed to authenticate with OpenAI"

- Verify your API key is valid
- Check your OpenAI account status
- Ensure you have sufficient credits

### Import Errors

```bash
# Ensure all dependencies are installed
uv sync --all-packages
```
