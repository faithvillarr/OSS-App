# Welcome to the OSS-APP

This project is a professional-grade Python application that integrates ticketing systems with AI and chatbot capabilities. Currently, the project includes the core ticketing integration built on a component-based architecture with a clear separation between interface and implementation.

**Current Status**: The ticketing integration is complete and functional. AI and chatbot features are planned for future development.

This documentation site provides an overview of the project's architecture, API contracts, and usage guidelines.

## Project Structure

The project is organized into several component libraries:

### Tickets Libraries

- **[Tickets API](libraries/tickets_api.md)**: Abstract interface for ticketing operations
- **[Tickets Implementation](libraries/tickets_client_impl.md)**: Google Tasks-based ticket implementation

### Task Client Libraries

- **[Task Client API](libraries/task_client_api.md)**: Abstract interface for task operations
- **[Google Tasks Implementation](libraries/gtask_client_impl.md)**: Google Tasks API implementation
- **[Task Service](libraries/task_client_service.md)**: FastAPI service for task operations
- **[Task Service Client](libraries/task_client_service_client.md)**: Auto-generated service client
- **[Task Adapter](libraries/task_client_adapter.md)**: Adapter for service-based task operations

## Quick Start

### Tickets Client

The tickets client provides a high-level interface for managing tickets using Google Tasks as the backend:

```python
import gtask_client_impl  # noqa: F401
from tickets_client_impl import TicketsClient
from tickets_api import TicketStatus

client = TicketsClient(interactive=False)

# Create a ticket
ticket = client.create_ticket(
    title="Fix bug in authentication",
    description="The login flow is broken"
)

# Search tickets
open_tickets = client.search_tickets(status=TicketStatus.OPEN)

# Update ticket status
updated = client.update_ticket(
    ticket_id=ticket.id,
    status=TicketStatus.IN_PROGRESS
)
```

### Task Client

The task client provides direct access to Google Tasks operations:

```python
import gtask_client_impl
from task_client_api import get_client

client = get_client(interactive=False)
tasklists = client.list_tasklists()
tasks = client.list_tasks(tasklist_id)
```

## Documentation

Each library has comprehensive documentation accessible through the navigation menu. All libraries include:

- Overview and purpose
- API reference
- Usage examples
- Architecture details
- Testing guidelines
