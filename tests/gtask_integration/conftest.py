"""Configuration for integration tests to handle dependency injection isolation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator
from dataclasses import dataclass
from typing import Never
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient
from task_client_adapter.service_task import register as register_task
from task_client_adapter.service_tasklist import register as register_tasklist
from task_client_service import app as service_app
from task_client_service import get_task_client

import gtask_client_impl
import task_client_api
from task_client_api import Client, Task, TaskList


@pytest.fixture(autouse=True)
def reset_dependency_injection() -> Generator[None, None, None]:
    """Reset dependency injection before each test to ensure test isolation.

    This fixture runs automatically before each test function to ensure that
    dependency injection from previous tests doesn't interfere with the current test.
    """
    # Store the original get_client function
    original_get_client = getattr(task_client_api, "get_client", None)

    # Reset to the original implementation (which raises NotImplementedError)
    def reset_get_client(*, interactive: bool = False) -> Never:
        """Reset to original implementation that raises NotImplementedError."""
        msg = "Dependency injection not properly set up"
        raise NotImplementedError(msg)

    # Set the reset function
    task_client_api.get_client = reset_get_client

    yield

    # Restore the original function after the test
    if original_get_client:
        task_client_api.get_client = original_get_client


@pytest.fixture(autouse=True)
def reset_task_dependency_injection() -> Generator[None, None, None]:
    """Reset task dependency injection before each test to ensure test isolation."""
    # Store the original get_task function
    original_get_task = getattr(task_client_api.task, "get_task", None)

    # Reset to the original implementation (which raises NotImplementedError)
    def reset_get_task(raw_data: str) -> Never:
        """Reset to original implementation that raises NotImplementedError."""
        msg = "Task dependency injection not properly set up"
        raise NotImplementedError(msg)

    # Set the reset function
    task_client_api.task.get_task = reset_get_task

    yield

    # Restore the original function after the test
    if original_get_task:
        task_client_api.task.get_task = original_get_task


@pytest.fixture(autouse=True)
def reset_tasklist_dependency_injection() -> Generator[None, None, None]:
    """Reset tasklist dependency injection before each test to ensure test isolation."""
    # Store the original get_tasklist function
    original_get_tasklist = getattr(task_client_api.tasklist, "get_tasklist", None)

    # Reset to the original implementation (which raises NotImplementedError)
    def reset_get_tasklist(raw_data: str) -> Never:
        """Reset to original implementation that raises NotImplementedError."""
        msg = "Tasklist dependency injection not properly set up"
        raise NotImplementedError(msg)

    # Set the reset function
    task_client_api.tasklist.get_tasklist = reset_get_tasklist

    yield

    # Restore the original function after the test
    if original_get_tasklist:
        task_client_api.tasklist.get_tasklist = original_get_tasklist


@dataclass
class MockServiceContext:
    """Context for running service with mock client."""

    base_url: str
    mock_tasklist_data: dict
    mock_task_data: dict
    httpx_client: TestClient
    mock_client: Client


@dataclass
class MockClientContext:
    """Context for creating mock client side effects."""

    default_tasklist: MagicMock
    mock_tasklist: MagicMock
    mock_task: MagicMock
    mock_tasklist_data: dict[str, str]
    mock_task_data: dict[str, str | bool | None]


class DummyTask:
    """Dummy task for testing."""

    def __init__(  # noqa: PLR0913
        self,
        task_id: str,
        title: str,
        tasklist_id: str,
        notes: str | None = None,
        status: str = "needsAction",
        due: str | None = None,
        completed: str | None = None,
        *,
        deleted: bool = False,
        hidden: bool = False,
    ) -> None:
        """Initialize the dummy task."""
        self.id = task_id
        self.title = title
        self.tasklist_id = tasklist_id
        self.notes = notes
        self.status = status
        self.due = due
        self.completed = completed
        self.deleted = deleted
        self.hidden = hidden


class DummyTaskList:
    """Dummy tasklist for testing."""

    def __init__(
        self,
        tasklist_id: str,
        title: str,
        etag: str = "etag-123",
        updated: str = "2025-01-15T10:30:00Z",
        self_link: str = "https://tasks.googleapis.com/tasks/v1/lists/tl_id",
    ) -> None:
        """Initialize the dummy tasklist."""
        self.id = tasklist_id
        self.title = title
        self.etag = etag
        self.updated = updated
        self.self_link = self_link


def _register_adapter_implementations() -> None:
    """Register adapter dependency injection implementations."""
    # Import and register the adapter implementation
    import task_client_adapter  # noqa: PLC0415

    task_client_adapter.register()

    # Also register the service task and tasklist implementations

    register_task()

    register_tasklist()


@pytest.fixture
def setup_adapter_dependency_injection() -> None:
    """Set up adapter dependency injection for tests that need it."""
    _register_adapter_implementations()


def _create_mock_tasklist_data() -> dict[str, str]:
    """Create mock tasklist data dictionary."""
    return {
        "id": "test_tl_123",
        "title": "Test Integration TaskList",
        "etag": "etag-123",
        "updated": "2025-01-15T10:30:00Z",
        "self_link": "https://tasks.googleapis.com/tasks/v1/lists/test_tl_123",
    }


def _create_mock_task_data() -> dict[str, str | bool | None]:
    """Create mock task data dictionary."""
    return {
        "id": "test_task_123",
        "title": "Test Integration Task",
        "tasklist_id": "test_tl_123",
        "notes": "This is a test task for integration testing.",
        "status": "needsAction",
        "due": None,
        "completed": None,
        "deleted": False,
        "hidden": False,
    }


def _create_default_tasklist() -> MagicMock:
    """Create a default tasklist mock (first in list - cannot be deleted)."""
    default_tasklist = MagicMock()
    default_tasklist.id = "default_tl"
    default_tasklist.title = "Default TaskList"
    default_tasklist.etag = "etag-default"
    default_tasklist.updated = "2025-01-01T00:00:00Z"
    default_tasklist.self_link = "https://tasks.googleapis.com/tasks/v1/lists/default_tl"
    return default_tasklist


def _create_mock_tasklist(tasklist_data: dict[str, str]) -> MagicMock:
    """Create a mock tasklist from tasklist data."""
    mock_tasklist = MagicMock()
    mock_tasklist.id = tasklist_data["id"]
    mock_tasklist.title = tasklist_data["title"]
    mock_tasklist.etag = tasklist_data["etag"]
    mock_tasklist.updated = tasklist_data["updated"]
    mock_tasklist.self_link = tasklist_data["self_link"]
    return mock_tasklist


def _create_mock_task(task_data: dict[str, str | bool | None]) -> MagicMock:
    """Create a mock task from task data."""
    mock_task = MagicMock()
    mock_task.id = task_data["id"]
    mock_task.title = task_data["title"]
    mock_task.notes = task_data["notes"]
    mock_task.status = task_data["status"]
    mock_task.due = task_data["due"]
    mock_task.completed = task_data["completed"]
    mock_task.deleted = task_data["deleted"]
    mock_task.hidden = task_data["hidden"]
    return mock_task


def _create_list_tasklists_side_effect(
    default_tasklist: MagicMock,
    mock_tasklist: MagicMock,
) -> object:
    """Create side effect for list_tasklists method."""

    def list_tasklists_side_effect() -> list[TaskList]:
        return [default_tasklist, mock_tasklist]

    return list_tasklists_side_effect


def _create_insert_tasklist_side_effect(mock_tasklist: MagicMock) -> object:
    """Create side effect for insert_tasklist method."""

    def insert_tasklist_side_effect(tasklist: TaskList) -> TaskList:
        mock_tasklist.title = tasklist.title
        return mock_tasklist

    return insert_tasklist_side_effect


def _create_delete_tasklist_side_effect(
    mock_tasklist_data: dict[str, str],
) -> object:
    """Create side effect for delete_tasklist method."""

    def delete_tasklist_side_effect(tasklist_id: str) -> bool:
        return tasklist_id == mock_tasklist_data["id"]

    return delete_tasklist_side_effect


def _create_list_tasks_side_effect(
    mock_tasklist_data: dict[str, str],
    mock_task: MagicMock,
) -> object:
    """Create side effect for list_tasks method."""

    def list_tasks_side_effect(tasklist_id: str) -> list[Task]:
        if tasklist_id == mock_tasklist_data["id"]:
            return [mock_task]
        return []

    return list_tasks_side_effect


def _create_get_task_side_effect(
    mock_tasklist_data: dict[str, str],
    mock_task_data: dict[str, str | bool | None],
    mock_task: MagicMock,
) -> object:
    """Create side effect for get_task method."""

    def get_task_side_effect(tasklist_id: str, task_id: str) -> Task:
        if task_id == mock_task_data["id"] and tasklist_id == mock_tasklist_data["id"]:
            return mock_task
        msg = f"Task with ID {task_id} not found"
        raise RuntimeError(msg)

    return get_task_side_effect


def _create_insert_task_side_effect(
    mock_tasklist_data: dict[str, str],
    mock_task: MagicMock,
) -> object:
    """Create side effect for insert_task method."""

    def insert_task_side_effect(tasklist_id: str) -> Task:
        if tasklist_id == mock_tasklist_data["id"]:
            return mock_task
        msg = f"Tasklist with ID {tasklist_id} not found"
        raise RuntimeError(msg)

    return insert_task_side_effect


def _create_delete_task_side_effect(
    mock_tasklist_data: dict[str, str],
    mock_task_data: dict[str, str | bool | None],
) -> object:
    """Create side effect for delete_task method."""

    def delete_task_side_effect(tasklist_id: str, task_id: str) -> bool:
        return task_id == mock_task_data["id"] and tasklist_id == mock_tasklist_data["id"]

    return delete_task_side_effect


def _configure_mock_client_side_effects(
    mock_client: MagicMock,
    context: MockClientContext,
) -> None:
    """Configure all side effects on the mock client."""
    mock_client.list_tasklists.side_effect = _create_list_tasklists_side_effect(context.default_tasklist, context.mock_tasklist)
    mock_client.insert_tasklist.side_effect = _create_insert_tasklist_side_effect(context.mock_tasklist)
    mock_client.delete_tasklist.side_effect = _create_delete_tasklist_side_effect(context.mock_tasklist_data)
    mock_client.list_tasks.side_effect = _create_list_tasks_side_effect(context.mock_tasklist_data, context.mock_task)
    mock_client.get_task.side_effect = _create_get_task_side_effect(
        context.mock_tasklist_data, context.mock_task_data, context.mock_task
    )
    mock_client.insert_task.side_effect = _create_insert_task_side_effect(context.mock_tasklist_data, context.mock_task)
    mock_client.delete_task.side_effect = _create_delete_task_side_effect(context.mock_tasklist_data, context.mock_task_data)


def _verify_mock_client_methods(mock_client: MagicMock) -> None:
    """Verify that all required methods exist on the mock client."""
    required_methods = [
        "list_tasklists",
        "insert_tasklist",
        "delete_tasklist",
        "list_tasks",
        "get_task",
        "insert_task",
        "delete_task",
    ]
    for method in required_methods:
        assert hasattr(mock_client, method), f"Mock missing {method} method"


@pytest.fixture
def mock_gtask_client() -> tuple[MagicMock, dict[str, str], dict[str, str]]:
    """Create a mock GTask client with test data."""
    mock_tasklist_data = _create_mock_tasklist_data()
    mock_task_data = _create_mock_task_data()

    default_tasklist = _create_default_tasklist()
    mock_tasklist = _create_mock_tasklist(mock_tasklist_data)
    mock_task = _create_mock_task(mock_task_data)

    mock_gtask_client = MagicMock(spec=gtask_client_impl.GTaskClient)

    context = MockClientContext(
        default_tasklist=default_tasklist,
        mock_tasklist=mock_tasklist,
        mock_task=mock_task,
        mock_tasklist_data=mock_tasklist_data,
        mock_task_data=mock_task_data,
    )
    _configure_mock_client_side_effects(mock_gtask_client, context)
    _verify_mock_client_methods(mock_gtask_client)

    return mock_gtask_client, mock_tasklist_data, mock_task_data


@pytest.fixture
def running_service_with_mock_client(
    mock_gtask_client: tuple[MagicMock, dict[str, str], dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> MockServiceContext:
    """Start a FastAPI service with a mocked GTask client."""
    mock_client, mock_tasklist_data, mock_task_data = mock_gtask_client

    # CRITICAL: Patch the get_client function BEFORE any imports
    # This ensures the real GTask client is NEVER used
    def mock_get_client(*args, **kwargs) -> MagicMock:  # noqa: ARG001, ANN003, ANN002
        return mock_client

    # Patch the get_client function in task_client_api
    monkeypatch.setattr(task_client_api, "get_client", mock_get_client, raising=True)

    # Also patch the GTaskClient class itself to prevent instantiation
    monkeypatch.setattr(
        gtask_client_impl,
        "GTaskClient",
        lambda: mock_client,
        raising=True,
    )

    # CRITICAL: Override the FastAPI app's state to use our mock client
    # This bypasses the lifespan function
    service_app.state.task_client = mock_client

    # Also override the FastAPI dependency to use our mock client
    service_app.dependency_overrides[get_task_client] = lambda: mock_client  # type: ignore[assignment]

    # Start the service using TestClient (in-process test client, not a real HTTP server)
    # TestClient simulates HTTP requests and exercises the full FastAPI application stack
    # This is the standard approach for integration testing and validates layer connectivity
    base_url = "http://testserver"
    try:
        with TestClient(service_app, base_url=base_url) as httpx_client:
            yield MockServiceContext(
                base_url=base_url,
                mock_tasklist_data=mock_tasklist_data,
                mock_task_data=mock_task_data,
                httpx_client=httpx_client,
                mock_client=mock_client,
            )
    finally:
        service_app.dependency_overrides.clear()
