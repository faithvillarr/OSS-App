"""Integration tests for the adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

import pytest
from starlette.testclient import TestClient

try:
    from task_client_adapter.service_client_adapter import ServiceClientAdapter
    from task_client_service import app as service_app
    from task_client_service import get_task_client
    from task_client_service_client import Client as ServiceClient
except ImportError:
    pytest.skip("task_client_adapter and task_client_service not available", allow_module_level=True)

import gtask_client_impl
import task_client_api
from task_client_api import Client, Task

from .conftest import (
    DummyTask,
    DummyTaskList,
    MockServiceContext,
    _register_adapter_implementations,
)


@pytest.fixture(autouse=True)
def setup_adapter_dependency_injection() -> None:
    """Set up adapter dependency injection for each test in this file."""
    _register_adapter_implementations()


def _configure_mock_client_for_adapter_tests(
    mock_client: MagicMock,
    default_tasklist: DummyTaskList,
    dummy_tasklist: DummyTaskList,
    dummy_task: DummyTask,
) -> None:
    """Configure mock client return values for adapter tests."""
    mock_client.list_tasklists.return_value = [default_tasklist, dummy_tasklist]
    mock_client.insert_tasklist.return_value = dummy_tasklist
    mock_client.delete_tasklist.return_value = True
    mock_client.list_tasks.return_value = [dummy_task]
    mock_client.get_task.return_value = dummy_task
    mock_client.insert_task.return_value = dummy_task
    mock_client.delete_task.return_value = True


def _setup_mock_client_injection(
    mock_client: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Set up mock client injection for tests."""
    monkeypatch.setattr(task_client_api, "get_client", lambda: mock_client, raising=True)
    service_app.dependency_overrides[get_task_client] = lambda: mock_client  # type: ignore[assignment]


def _test_tasklist_operations(
    adapter: ServiceClientAdapter,
    dummy_tasklist: DummyTaskList,
) -> None:
    """Test tasklist operations via adapter."""
    got_tasklists = adapter.list_tasklists()
    assert len(got_tasklists) >= 1
    test_tasklist = next((tl for tl in got_tasklists if tl.id == dummy_tasklist.id), None)
    assert test_tasklist is not None
    assert test_tasklist.id == dummy_tasklist.id
    assert test_tasklist.title == dummy_tasklist.title

    inserted_tasklist = adapter.insert_tasklist(dummy_tasklist)
    assert inserted_tasklist.id == dummy_tasklist.id
    assert inserted_tasklist.title == dummy_tasklist.title


def _test_task_operations(
    adapter: ServiceClientAdapter,
    dummy_tasklist: DummyTaskList,
    dummy_task: DummyTask,
) -> None:
    """Test task operations via adapter."""
    got_tasks = adapter.list_tasks(dummy_tasklist.id)
    assert len(got_tasks) == 1
    assert got_tasks[0].id == dummy_task.id
    assert got_tasks[0].title == dummy_task.title

    got_one: Task = adapter.get_task(dummy_tasklist.id, dummy_task.id)
    assert got_one.id == dummy_task.id
    assert got_one.title == dummy_task.title

    inserted_task = adapter.insert_task(dummy_tasklist.id, dummy_task)
    assert inserted_task.id == dummy_task.id
    assert inserted_task.title == dummy_task.title


def _test_delete_operations(
    adapter: ServiceClientAdapter,
    dummy_tasklist: DummyTaskList,
    dummy_task: DummyTask,
) -> None:
    """Test delete operations via adapter."""
    delete_tasklist_success = adapter.delete_tasklist(dummy_tasklist.id)
    assert delete_tasklist_success is True

    delete_task_success = adapter.delete_task(dummy_tasklist.id, dummy_task.id)
    assert delete_task_success is True


def _verify_mock_client_calls(
    mock_client: MagicMock,
    dummy_tasklist: DummyTaskList,
    dummy_task: DummyTask,
) -> None:
    """Verify all mock client calls were made correctly."""
    assert mock_client.list_tasklists.call_count >= 1

    mock_client.insert_tasklist.assert_called_once()
    call_args = mock_client.insert_tasklist.call_args
    assert call_args is not None
    assert len(call_args[0]) == 1, "insert_tasklist should be called with one TaskList argument"
    inserted_tasklist = call_args[0][0]
    assert inserted_tasklist.title == dummy_tasklist.title

    mock_client.list_tasks.assert_called_once_with(dummy_tasklist.id)
    mock_client.get_task.assert_called_once_with(dummy_tasklist.id, dummy_task.id)

    mock_client.insert_task.assert_called_once()
    insert_task_call_args = mock_client.insert_task.call_args
    assert insert_task_call_args is not None
    assert insert_task_call_args[0][0] == dummy_tasklist.id, "First arg should be tasklist_id"
    inserted_task = insert_task_call_args[0][1]
    assert inserted_task.title == dummy_task.title

    mock_client.delete_tasklist.assert_called_once_with(dummy_tasklist.id)
    mock_client.delete_task.assert_called_once_with(dummy_tasklist.id, dummy_task.id)


def _create_mock_tasklist_from_data(tasklist_data: dict[str, str]) -> MagicMock:
    """Create a mock tasklist from data dictionary."""
    mock_tasklist = MagicMock()
    mock_tasklist.id = tasklist_data["id"]
    mock_tasklist.title = tasklist_data["title"]
    mock_tasklist.etag = tasklist_data["etag"]
    mock_tasklist.updated = tasklist_data["updated"]
    mock_tasklist.self_link = tasklist_data["self_link"]
    return mock_tasklist


def _create_mock_task_from_data(task_data: dict[str, str | bool | None]) -> MagicMock:
    """Create a mock task from data dictionary."""
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


def _create_default_mock_tasklist() -> MagicMock:
    """Create a default mock tasklist."""
    default_tasklist = MagicMock()
    default_tasklist.id = "default_tl"
    default_tasklist.title = "Default TaskList"
    default_tasklist.etag = "etag-default"
    default_tasklist.updated = "2025-01-01T00:00:00Z"
    default_tasklist.self_link = "https://tasks.googleapis.com/tasks/v1/lists/default_tl"
    return default_tasklist


def _configure_mock_gtask_client(
    mock_gtask_client: MagicMock,
    default_tasklist: MagicMock,
    mock_tasklist: MagicMock,
    mock_task: MagicMock,
) -> None:
    """Configure mock GTask client return values."""
    mock_gtask_client.list_tasklists.return_value = [default_tasklist, mock_tasklist]
    mock_gtask_client.insert_tasklist.return_value = mock_tasklist
    mock_gtask_client.delete_tasklist.return_value = True
    mock_gtask_client.list_tasks.return_value = [mock_task]
    mock_gtask_client.get_task.return_value = mock_task
    mock_gtask_client.insert_task.return_value = mock_task
    mock_gtask_client.delete_task.return_value = True


def _test_tasklist_operations_with_mock_data(
    adapter: ServiceClientAdapter,
    mock_tasklist: MagicMock,
    mock_tasklist_data: dict[str, str],
) -> None:
    """Test tasklist operations with mock data."""
    retrieved_tasklists = adapter.list_tasklists()
    assert len(retrieved_tasklists) >= 1
    test_tasklist = next(
        (tl for tl in retrieved_tasklists if tl.id == mock_tasklist_data["id"]),
        None,
    )
    assert test_tasklist is not None
    assert test_tasklist.id == mock_tasklist_data["id"]
    assert test_tasklist.title == mock_tasklist_data["title"]

    inserted_tasklist = adapter.insert_tasklist(mock_tasklist)
    assert inserted_tasklist.id == mock_tasklist_data["id"]
    assert inserted_tasklist.title == mock_tasklist_data["title"]


def _test_task_operations_with_mock_data(
    adapter: ServiceClientAdapter,
    mock_task: MagicMock,
    mock_tasklist_data: dict[str, str],
    mock_task_data: dict[str, str | bool | None],
) -> None:
    """Test task operations with mock data."""
    retrieved_tasks = adapter.list_tasks(mock_tasklist_data["id"])
    assert len(retrieved_tasks) == 1
    first_task = retrieved_tasks[0]
    assert first_task.id == mock_task_data["id"]
    assert first_task.title == mock_task_data["title"]

    retrieved_task = adapter.get_task(mock_tasklist_data["id"], mock_task_data["id"])
    assert retrieved_task.id == mock_task_data["id"]
    assert retrieved_task.title == mock_task_data["title"]
    assert retrieved_task.notes == mock_task_data["notes"]

    inserted_task = adapter.insert_task(mock_tasklist_data["id"], mock_task)
    assert inserted_task.id == mock_task_data["id"]
    assert inserted_task.title == mock_task_data["title"]


def _test_delete_operations_with_mock_data(
    adapter: ServiceClientAdapter,
    mock_tasklist_data: dict[str, str],
    mock_task_data: dict[str, str | bool | None],
) -> None:
    """Test delete operations with mock data."""
    assert adapter.delete_tasklist(mock_tasklist_data["id"]) is True
    assert adapter.delete_task(mock_tasklist_data["id"], mock_task_data["id"]) is True


def _verify_mock_gtask_client_calls(
    mock_gtask_client: MagicMock,
    mock_tasklist_data: dict[str, str],
    mock_task_data: dict[str, str | bool | None],
) -> None:
    """Verify all mock GTask client calls were made correctly."""
    mock_gtask_client.list_tasklists.assert_called()
    mock_gtask_client.insert_tasklist.assert_called()
    mock_gtask_client.delete_tasklist.assert_called_with(mock_tasklist_data["id"])
    mock_gtask_client.list_tasks.assert_called_with(mock_tasklist_data["id"])
    mock_gtask_client.get_task.assert_called_with(mock_tasklist_data["id"], mock_task_data["id"])
    mock_gtask_client.insert_task.assert_called()
    mock_gtask_client.delete_task.assert_called_with(mock_tasklist_data["id"], mock_task_data["id"])


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_exercises_service_and_task_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the adapter exercises the service and task client."""
    mock_client = create_autospec(Client, spec_set=True)

    default_tasklist = DummyTaskList("default_tl", "Default TaskList")
    dummy_tasklist = DummyTaskList("int_tl", "Integration Test TaskList")
    dummy_task = DummyTask(
        "int_task",
        "Integration Test Task",
        "int_tl",
        "This is an integration test task body.",
    )

    _configure_mock_client_for_adapter_tests(mock_client, default_tasklist, dummy_tasklist, dummy_task)
    _setup_mock_client_injection(mock_client, monkeypatch)

    try:
        base_url = "http://testserver"
        with TestClient(service_app, base_url=base_url) as httpx_client:
            service_client = ServiceClient(base_url=base_url)
            service_client.set_httpx_client(httpx_client)
            adapter = ServiceClientAdapter(service_client)

            _test_tasklist_operations(adapter, dummy_tasklist)
            _test_task_operations(adapter, dummy_tasklist, dummy_task)
            _test_delete_operations(adapter, dummy_tasklist, dummy_task)
            _verify_mock_client_calls(mock_client, dummy_tasklist, dummy_task)
    finally:
        service_app.dependency_overrides.pop(get_task_client, None)


@pytest.mark.integration
@pytest.mark.local_credentials
def test_end_to_end_service_call_with_mocked_gtask_impl_and_fastapi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that verifies end-to-end service call with all layers connected.

    This test verifies:
    1. task_client_adapter calls the running task_client_service (via HTTP)
    2. task_client_service calls the mocked gtask_client_impl
    3. All layers are connected correctly and data flows through them

    Flow: adapter -> service (HTTP) -> mocked gtask_client_impl
    """
    mock_tasklist_data = {
        "id": "circleci_tl_123",
        "title": "CircleCI End-to-End Test TaskList",
        "etag": "etag-123",
        "updated": "2025-10-04T14:30:00Z",
        "self_link": "https://tasks.googleapis.com/tasks/v1/lists/circleci_tl_123",
    }

    mock_task_data = {
        "id": "circleci_task_123",
        "title": "CircleCI End-to-End Test Task",
        "tasklist_id": "circleci_tl_123",
        "notes": "This task tests the full integration stack in CI.",
        "status": "needsAction",
        "due": None,
        "completed": None,
        "deleted": False,
        "hidden": False,
    }

    default_tasklist = _create_default_mock_tasklist()
    mock_tasklist = _create_mock_tasklist_from_data(mock_tasklist_data)
    mock_task = _create_mock_task_from_data(mock_task_data)

    mock_gtask_client = MagicMock(spec=gtask_client_impl.GTaskClient)
    _configure_mock_gtask_client(mock_gtask_client, default_tasklist, mock_tasklist, mock_task)

    monkeypatch.setattr(task_client_api, "get_client", lambda: mock_gtask_client, raising=True)
    service_app.dependency_overrides[get_task_client] = lambda: mock_gtask_client  # type: ignore[assignment]

    try:
        base_url = "http://testserver"
        with TestClient(service_app, base_url=base_url) as httpx_client:
            service_client = ServiceClient(base_url=base_url)
            service_client.set_httpx_client(httpx_client)
            adapter = ServiceClientAdapter(service_client)

            _test_tasklist_operations_with_mock_data(adapter, mock_tasklist, mock_tasklist_data)
            _test_task_operations_with_mock_data(adapter, mock_task, mock_tasklist_data, mock_task_data)
            _test_delete_operations_with_mock_data(adapter, mock_tasklist_data, mock_task_data)
            _verify_mock_gtask_client_calls(mock_gtask_client, mock_tasklist_data, mock_task_data)
    finally:
        service_app.dependency_overrides.pop(get_task_client, None)


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_with_running_service_and_mock_gtask_client(
    running_service_with_mock_client: MockServiceContext,
) -> None:
    """Test adapter with a running FastAPI service using a mock GTask client.

    All operations go through: adapter -> service -> mocked gtask_client_impl
    """
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    tasklists = adapter.list_tasklists()
    assert len(tasklists) >= 1
    test_tasklist = next(
        (tl for tl in tasklists if tl.id == running_service_with_mock_client.mock_tasklist_data["id"]),
        None,
    )
    assert test_tasklist is not None
    assert test_tasklist.id == running_service_with_mock_client.mock_tasklist_data["id"]
    assert test_tasklist.title == running_service_with_mock_client.mock_tasklist_data["title"]
    assert test_tasklist.etag == running_service_with_mock_client.mock_tasklist_data["etag"]
    assert test_tasklist.updated == running_service_with_mock_client.mock_tasklist_data["updated"]
    assert test_tasklist.self_link == running_service_with_mock_client.mock_tasklist_data["self_link"]

    running_service_with_mock_client.mock_client.list_tasklists.assert_called_once()

    mock_tasklist_obj = MagicMock()
    mock_tasklist_obj.id = running_service_with_mock_client.mock_tasklist_data["id"]
    mock_tasklist_obj.title = running_service_with_mock_client.mock_tasklist_data["title"]
    mock_tasklist_obj.etag = running_service_with_mock_client.mock_tasklist_data["etag"]
    mock_tasklist_obj.updated = running_service_with_mock_client.mock_tasklist_data["updated"]
    mock_tasklist_obj.self_link = running_service_with_mock_client.mock_tasklist_data["self_link"]

    inserted_tasklist = adapter.insert_tasklist(mock_tasklist_obj)
    assert inserted_tasklist.id == running_service_with_mock_client.mock_tasklist_data["id"]
    assert inserted_tasklist.title == running_service_with_mock_client.mock_tasklist_data["title"]

    running_service_with_mock_client.mock_client.insert_tasklist.assert_called()

    tasks = adapter.list_tasks(running_service_with_mock_client.mock_tasklist_data["id"])
    assert len(tasks) == 1
    first_task = tasks[0]
    assert first_task.id == running_service_with_mock_client.mock_task_data["id"]
    assert first_task.title == running_service_with_mock_client.mock_task_data["title"]
    assert first_task.notes == running_service_with_mock_client.mock_task_data["notes"]
    assert first_task.status == running_service_with_mock_client.mock_task_data["status"]

    running_service_with_mock_client.mock_client.list_tasks.assert_called_once_with(
        running_service_with_mock_client.mock_tasklist_data["id"]
    )

    retrieved_task = adapter.get_task(
        running_service_with_mock_client.mock_tasklist_data["id"],
        running_service_with_mock_client.mock_task_data["id"],
    )
    assert retrieved_task.id == running_service_with_mock_client.mock_task_data["id"]
    assert retrieved_task.title == running_service_with_mock_client.mock_task_data["title"]
    assert retrieved_task.notes == running_service_with_mock_client.mock_task_data["notes"]
    assert retrieved_task.status == running_service_with_mock_client.mock_task_data["status"]

    running_service_with_mock_client.mock_client.get_task.assert_called_once_with(
        running_service_with_mock_client.mock_tasklist_data["id"],
        running_service_with_mock_client.mock_task_data["id"],
    )

    delete_success = adapter.delete_tasklist(running_service_with_mock_client.mock_tasklist_data["id"])
    assert delete_success is True

    running_service_with_mock_client.mock_client.delete_tasklist.assert_called_once_with(
        running_service_with_mock_client.mock_tasklist_data["id"]
    )

    delete_task_success = adapter.delete_task(
        running_service_with_mock_client.mock_tasklist_data["id"],
        running_service_with_mock_client.mock_task_data["id"],
    )
    assert delete_task_success is True

    running_service_with_mock_client.mock_client.delete_task.assert_called_once_with(
        running_service_with_mock_client.mock_tasklist_data["id"],
        running_service_with_mock_client.mock_task_data["id"],
    )


@pytest.mark.integration
@pytest.mark.local_credentials
def test_verify_mock_gtask_client_isolation(
    running_service_with_mock_client: MockServiceContext,
) -> None:
    """Verify that we are NEVER using the real GTask client.

    All operations go through: adapter -> service -> mocked gtask_client_impl
    """
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    tasklists = adapter.list_tasklists()
    assert len(tasklists) >= 1

    tasklist = next(
        (tl for tl in tasklists if tl.id == "test_tl_123"),
        None,
    )
    assert tasklist is not None

    assert tasklist.id == "test_tl_123"
    assert tasklist.title == "Test Integration TaskList"

    with pytest.raises(RuntimeError, match="Task with ID invalid-task-id not found"):
        adapter.get_task("test_tl_123", "invalid-task-id")

    running_service_with_mock_client.mock_client.list_tasklists.assert_called_once()
    running_service_with_mock_client.mock_client.get_task.assert_called_once_with("test_tl_123", "invalid-task-id")
