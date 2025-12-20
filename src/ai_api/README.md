# AI API

## Overview
`ai_api` defines the abstract interface (contract) for AI services in this application. It provides the `AIInterface` ABC that all AI implementations must follow, enabling dependency injection and implementation swapping.

## Purpose

This package serves as the foundation for the AI service architecture:

- **Abstract Base Class (ABC)**: Defines the contract that all AI implementations must fulfill
- **Dependency Injection**: Provides a `get_client()` factory function that returns the registered implementation
- **Implementation Agnostic**: Consumer code depends only on the interface, not specific implementations
- **Flexible Architecture**: Allows switching between local (OpenAI) and remote (AI Service) implementations

## Architecture

The AI API follows the **Interface-Implementation Separation** pattern:

```
ai_api (Interface/Contract)
    ↑
    ├── openai_impl (Local Implementation)
    └── ai_adapter (Remote Service Implementation)
```

### Key Components

1. **AIInterface (ABC)**: Abstract base class defining the contract
2. **get_client()**: Factory function that returns the registered implementation

## API Reference

### AIInterface

Abstract base class that defines the contract for AI services.

#### Methods

```python
@abstractmethod
def generate_response(
    user_input: str,
    system_prompt: str,
    response_schema: dict[str, Any] | None = None,
) -> str | dict[str, Any]:
    """Generate a response from the AI.
    
    Args:
        user_input: The text provided by the chat user
        system_prompt: The instruction set (e.g., "You are a helpful assistant...")
        response_schema: Optional JSON schema dict for structured output
        
    Returns:
        str: Conversational response (when response_schema is None)
        dict: Structured data matching the schema (when response_schema is provided)
    """
```

### Factory Function

```python
def get_client() -> AIInterface:
    """Return an instance of the registered AI client implementation."""
```

## Usage Examples

### Basic Usage (with Implementation)

```python
import openai_impl  # Registers the OpenAI implementation
from ai_api import get_client

# Get the registered client
client = get_client()

# Conversational response
response = client.generate_response(
    user_input="What is the capital of France?",
    system_prompt="You are a helpful geography assistant."
)
print(response)  # "The capital of France is Paris."
```

### Structured Output

```python
from ai_api import get_client

client = get_client()

# Define a schema for structured output
schema = {
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

# Get structured response
result = client.generate_response(
    user_input="Create a ticket to fix login redirect.",
    system_prompt="Extract intent and title fields.",
    response_schema=schema,
)
print(result)  # {"intent": "create_ticket", "title": "Fix login redirect"}
```

### Switching Implementations

The beauty of this architecture is that you can switch implementations without changing consumer code:

```python
# Option 1: Use local OpenAI implementation
import openai_impl  # Auto-registers on import
from ai_api import get_client

client = get_client()  # Returns OpenAIClient

# Option 2: Use remote AI service
import ai_adapter
ai_adapter.register(base_url="http://localhost:8000")
from ai_api import get_client

client = get_client()  # Returns ServiceClient (calls remote API)

# Consumer code remains identical!
response = client.generate_response("Hello", "You are helpful.")
```

## Dependency Injection Pattern

The `get_client()` function is designed to be "patched" by implementations:

```python
import ai_api
from ai_api import AIInterface

# Initially, get_client() raises NotImplementedError
try:
    client = ai_api.get_client()
except NotImplementedError:
    print("No implementation registered yet")

# Implementations register themselves by patching get_client()
def register_my_impl():
    def _get_client() -> AIInterface:
        return MyCustomAIClient()
    
    ai_api.get_client = _get_client

# Now get_client() returns your implementation
register_my_impl()
client = ai_api.get_client()  # Returns MyCustomAIClient instance
```

## Response Schema Format

When using structured output, the `response_schema` should follow this format:

```python
{
    "name": "schema_name",           # Name of the schema
    "description": "What it does",   # Description of the schema
    "schema": {                      # JSON Schema specification
        "type": "object",
        "properties": {
            "field1": {"type": "string"},
            "field2": {"type": "integer"}
        },
        "required": ["field1"],
        "additionalProperties": False
    }
}
```

## Testing

```bash
# Run unit tests
uv run pytest src/ai_api/tests/ -v

# Run with coverage
uv run pytest src/ai_api/tests/ --cov=src/ai_api --cov-report=term-missing
```

## Integration with Other Components

- **openai_impl**: Provides concrete implementation using OpenAI API
- **ai_service**: FastAPI service that exposes the interface via REST endpoints
- **ai_adapter**: Adapter that wraps the service client to match this interface
- **ai_service_client**: Auto-generated client for calling the AI service

## Design Principles

1. **Single Responsibility**: Defines only the contract, no implementation details
2. **Open/Closed**: Open for extension (new implementations), closed for modification
3. **Dependency Inversion**: High-level code depends on abstractions, not concrete implementations
4. **Interface Segregation**: Minimal, focused interface with only essential methods
