# Tickets API

## Overview

`tickets_api` defines the abstract interface (contract) for ticketing services in this application. It provides the `TicketInterface` ABC and `Ticket` base class that all ticket implementations must follow, enabling dependency injection and implementation swapping.

## Purpose

This package serves as the foundation for the ticketing architecture:

- **Abstract Base Class (ABC)**: Defines the contract that all ticket implementations must fulfill
- **Type Safety**: Provides `Ticket` and `TicketStatus` abstractions for type checking
- **Implementation Agnostic**: Consumer code depends only on the interface, not specific implementations
- **Flexible Architecture**: Allows switching between different backend implementations (Google Tasks, Jira, etc.)

## Architecture

The Tickets API follows the **Interface-Implementation Separation** pattern:

```
tickets_api (Interface/Contract)
    ↑
    └── tickets_client_impl (Google Tasks Implementation)
```

## API Reference

### TicketStatus Enum

```python
class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
```

### Ticket Abstract Base Class

```python
class Ticket(ABC):
    @property
    def id(self) -> str: ...
    
    @property
    def title(self) -> str: ...
    
    @property
    def description(self) -> str: ...
    
    @property
    def status(self) -> TicketStatus: ...
    
    @property
    def assignee(self) -> str | None: ...
```

### TicketInterface Abstract Base Class

```python
class TicketInterface(ABC):
    @abstractmethod
    def create_ticket(
        self, 
        title: str, 
        description: str, 
        assignee: str | None = None
    ) -> Ticket: ...
    
    @abstractmethod
    def get_ticket(self, ticket_id: str) -> Ticket | None: ...
    
    @abstractmethod
    def search_tickets(
        self, 
        query: str | None = None, 
        status: TicketStatus | None = None
    ) -> list[Ticket]: ...
    
    @abstractmethod
    def update_ticket(
        self,
        ticket_id: str,
        status: TicketStatus | None = None,
        title: str | None = None,
    ) -> Ticket: ...
    
    @abstractmethod
    def delete_ticket(self, ticket_id: str) -> bool: ...
```

## Usage Examples

### Basic Usage (with Implementation)

```python
import tickets_client_impl  # Registers the Google Tasks implementation
from tickets_api import TicketStatus
from tickets_client_impl import TicketsClient

# Create client
client = TicketsClient(interactive=False)

# Create a ticket
ticket = client.create_ticket(
    title="Fix login bug",
    description="Users cannot authenticate after password reset"
)

# Get a ticket
ticket = client.get_ticket(ticket_id)

# Search tickets
open_tickets = client.search_tickets(status=TicketStatus.OPEN)
bug_tickets = client.search_tickets(query="bug")

# Update a ticket
updated = client.update_ticket(
    ticket_id,
    status=TicketStatus.IN_PROGRESS,
    title="Fix login bug (updated)"
)

# Delete a ticket
success = client.delete_ticket(ticket_id)
```

## Design Principles

1. **Single Responsibility**: Defines only the contract, no implementation details
2. **Open/Closed**: Open for extension (new implementations), closed for modification
3. **Dependency Inversion**: High-level code depends on abstractions, not concrete implementations
4. **Interface Segregation**: Minimal, focused interface with only essential methods

## Integration with Other Components

- **tickets_client_impl**: Provides concrete implementation using Google Tasks as the backend
- **main_service**: Uses `TicketInterface` for ticket operations in the Discord polling service
