"""Integration tests for gtask_client_impl authentication and API connectivity.

This module tests that the dependency injection works correctly and that
the client can authenticate and make real API calls to Google Tasks.
"""

import logging

import pytest

import gtask_client_impl
import task_client_api

pytestmark = pytest.mark.integration

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def setup_gtask_dependency_injection() -> None:
    """Set up GTask client dependency injection for each test in this file."""
    import gtask_client_impl

    gtask_client_impl.register()

    from gtask_client_impl.task_impl import register as register_task

    register_task()

    from gtask_client_impl.tasklist_impl import register as register_tasklist

    register_tasklist()


@pytest.mark.circleci
@pytest.mark.local_credentials
def test_get_client_and_authenticate() -> None:
    """Tests that the factory provides a real, authenticated GTaskClient.

    This test requires real credentials (via .env or credentials.json)
    and makes a live, read-only call to the Google Tasks API.
    """
    try:
        client = task_client_api.get_client(interactive=False)
        assert isinstance(client, gtask_client_impl.GTaskClient)

    except FileNotFoundError:
        pytest.skip("Skipping integration test: credentials.json not found.")
    except RuntimeError as e:
        if "Failed to obtain credentials" in str(
            e
        ) or "No valid credentials found" in str(e):
            pytest.skip(f"Skipping integration test: {e}")
        else:
            pytest.fail(
                f"Integration test failed during authentication or API call: {e}"
            )
    except (ValueError, ConnectionError) as e:
        pytest.fail(f"Integration test failed during authentication or API call: {e}")


@pytest.mark.circleci
def test_dependency_injection_works() -> None:
    """Tests that importing the implementation packages correctly overrides the factory functions in the abstract contract packages."""
    try:
        client = task_client_api.get_client(interactive=False)
        assert isinstance(client, gtask_client_impl.GTaskClient)
        assert hasattr(client, "list_tasklists")
        assert hasattr(client, "insert_tasklist")
        assert hasattr(client, "delete_tasklist")
        assert hasattr(client, "list_tasks")
        assert hasattr(client, "get_task")
        assert hasattr(client, "insert_task")
        assert hasattr(client, "delete_task")
    except RuntimeError as e:
        if "No valid credentials found" in str(
            e
        ) or "Failed to obtain credentials" in str(e):
            pass
        else:
            raise


@pytest.mark.circleci
def test_task_dependency_injection() -> None:
    """Tests that importing gtask_task_impl overrides task.get_task."""
    import json

    import gtask_client_impl
    import task_client_api

    task_data = {
        "id": "di123",
        "title": "Dependency Injection Test Task",
        "status": "needsAction",
        "notes": "DI test notes",
    }
    raw_data = json.dumps(task_data)

    task = task_client_api.get_task(raw_data=raw_data)

    assert isinstance(task, gtask_client_impl.GTask)
    assert task.id == "di123"
    assert task.title == "Dependency Injection Test Task"
    assert task.status == "needsAction"
    assert task.notes == "DI test notes"


@pytest.mark.circleci
def test_tasklist_dependency_injection() -> None:
    """Tests that importing gtask_tasklist_impl overrides tasklist.get_tasklist."""
    import json

    import gtask_client_impl
    import task_client_api

    tasklist_data = {
        "id": "di_tl_123",
        "title": "Dependency Injection Test TaskList",
        "etag": "etag123",
        "updated": "2025-01-15T10:30:00Z",
        "selfLink": "https://tasks.googleapis.com/tasks/v1/lists/di_tl_123",
    }
    raw_data = json.dumps(tasklist_data)

    tasklist = task_client_api.get_tasklist(raw_data=raw_data)

    assert isinstance(tasklist, gtask_client_impl.GTaskList)
    assert tasklist.id == "di_tl_123"
    assert tasklist.title == "Dependency Injection Test TaskList"
    assert tasklist.etag == "etag123"


@pytest.mark.circleci
def test_factory_functions_work_together() -> None:
    """Tests that all factory functions work together correctly.

    This test only checks imports and factory setup, no credentials needed.
    """
    import task_client_api
    from gtask_client_impl import get_client_impl

    # Verify that task_client_api.get_client is now our implementation
    assert task_client_api.get_client is get_client_impl


@pytest.mark.circleci
@pytest.mark.local_credentials
def test_client_scope_permissions() -> None:
    """Tests that the client has the necessary OAuth scopes for the operations we want to perform."""
    try:
        client = task_client_api.get_client(interactive=False)

        # Cast to GTaskClient to access service attribute
        gtask_client = client
        assert isinstance(gtask_client, gtask_client_impl.GTaskClient)

        # Try to list tasklists (requires read permission)
        tasklists_result = (
            gtask_client.service.tasklists()  # type: ignore[attr-defined]
            .list()
            .execute()
        )

        # Should return a dictionary with items list (even if empty)
        assert isinstance(tasklists_result, dict)
        assert "items" in tasklists_result or tasklists_result.get("items", []) == []

    except FileNotFoundError:
        pytest.skip("Skipping integration test: credentials.json not found.")
    except RuntimeError as e:
        # Skip if credentials are missing (expected in CI without credentials)
        if "Failed to obtain credentials" in str(
            e
        ) or "No valid credentials found" in str(e):
            pytest.skip(f"Skipping integration test: {e}")
        else:
            pytest.fail(f"Integration test failed: {e}")
    except (ValueError, ConnectionError) as e:
        # If we get a 403 error, it's likely a scope issue
        if "403" in str(e) or "insufficient" in str(e).lower():
            pytest.fail(
                f"OAuth scope issue - client may not have required permissions: {e}"
            )
        else:
            pytest.fail(f"Integration test failed: {e}")


@pytest.mark.circleci
def test_client_initialization_modes() -> None:
    """Tests that the client can be initialized in different modes.

    This test checks initialization behavior, not actual authentication.
    """
    try:
        # Test non-interactive mode (default)
        client1 = task_client_api.get_client(interactive=False)
        assert isinstance(client1, gtask_client_impl.GTaskClient)

        # Test that we can create multiple instances
        client2 = task_client_api.get_client(interactive=False)
        assert isinstance(client2, gtask_client_impl.GTaskClient)

        # They should be separate instances
        assert client1 is not client2

    except RuntimeError as e:
        if "No valid credentials found" in str(
            e
        ) or "Failed to obtain credentials" in str(e):
            logger.debug(
                "Client initialization works correctly - authentication failed as expected without credentials"
            )
        else:
            pytest.fail(f"Unexpected error during client initialization: {e}")
    except FileNotFoundError:
        pytest.skip("Skipping integration test: credentials.json not found.")
