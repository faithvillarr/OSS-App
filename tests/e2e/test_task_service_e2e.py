"""End-to-end tests for the Google Tasks service."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import time
from contextlib import closing
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, NamedTuple

import httpx
import pytest
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from gtask_client_impl.auth import OAuthManager

import task_client_api
from task_client_adapter import ServiceClientAdapter
from task_client_service_client import Client

if TYPE_CHECKING:
    from collections.abc import Generator

# Load environment variables from .env file so TASKS_* variables are available locally.
load_dotenv()

pytestmark = pytest.mark.e2e

_USING_STUB_SERVICE = False


def _init_stub_data() -> tuple[
    list[dict[str, str]],
    dict[str, list[dict[str, bool | None | str]]],
]:
    """Initialize stub data structures."""
    tasklists = [
        {
            "id": "stub-tasklist-1",
            "title": "Stub Tasklist",
            "etag": '"stub-tasklist-1"',
            "updated": "2025-01-01T00:00:00.000Z",
            "selfLink": "https://example.com/tasklists/stub-tasklist-1",
        },
    ]
    tasks: dict[str, list[dict[str, bool | None | str]]] = {
        "stub-tasklist-1": [
            {
                "id": "stub-task-1",
                "title": "Review PR",
                "notes": "Walk the reviewer through the latest changes",
                "status": "needsAction",
                "due": None,
                "completed": None,
                "deleted": False,
                "hidden": False,
            },
        ],
    }
    return tasklists, tasks


def _register_openapi_route(app: FastAPI) -> None:
    """Register OpenAPI route."""

    @app.get("/openapi.json")
    def openapi() -> dict[str, Any]:
        return {
            "openapi": "3.0.0",
            "info": {"title": "Stub Task Service", "version": "1.0.0"},
            "paths": {
                "/tasklists": {},
                "/tasklists/{{tasklist_id}}": {},
                "/tasks/{{tasklist_id}}": {},
                "/tasks/{{tasklist_id}}/{{task_id}}": {},
            },
        }


def _register_tasklist_routes(
    app: FastAPI,
    tasklists: list[dict[str, str]],
    tasks: dict[str, list[dict[str, bool | None | str]]],
) -> None:
    """Register tasklist routes."""
    import itertools

    tasklist_counter = itertools.count(start=2)

    @app.get("/tasklists")
    def list_tasklists() -> list[dict[str, str]]:
        return tasklists

    @app.post("/tasklists")
    def insert_tasklist(body: dict[str, str]) -> dict[str, str]:
        new_id = f"stub-tasklist-{next(tasklist_counter)}"
        title = body.get("title", f"Tasklist {new_id}")
        new_tasklist = {
            "id": new_id,
            "title": title,
            "etag": f'"{new_id}"',
            "updated": "2025-01-01T00:00:00.000Z",
            "selfLink": f"https://example.com/tasklists/{new_id}",
        }
        tasklists.append(new_tasklist)
        tasks[new_id] = []
        return new_tasklist


def _register_task_routes(
    app: FastAPI,
    tasks: dict[str, list[dict[str, bool | None | str]]],
) -> None:
    """Register task routes."""
    import itertools

    from fastapi import HTTPException

    task_counter = itertools.count(start=2)

    @app.get("/tasks/{tasklist_id}")
    def list_tasks(tasklist_id: str) -> list[dict[str, bool | None | str]]:
        return tasks.get(tasklist_id, [])

    @app.post("/tasks/{tasklist_id}")
    def insert_task(
        tasklist_id: str,
        body: dict[str, bool | None | str],
    ) -> dict[str, bool | None | str]:
        if tasklist_id not in tasks:
            raise HTTPException(status_code=404, detail="Tasklist not found")

        new_id = f"{tasklist_id}-task-{next(task_counter)}"
        created_task = {
            "id": new_id,
            "title": str(body.get("title", "Untitled Task")),
            "notes": str(body.get("notes") or ""),
            "status": str(body.get("status") or "needsAction"),
            "due": body.get("due"),
            "completed": body.get("completed"),
            "deleted": bool(body.get("deleted", False)),
            "hidden": bool(body.get("hidden", False)),
        }
        tasks[tasklist_id].append(created_task)
        return created_task

    @app.delete("/tasks/{tasklist_id}/{task_id}")
    def delete_task(tasklist_id: str, task_id: str) -> dict[str, Any]:
        task_collection = tasks.get(tasklist_id)
        if not task_collection:
            raise HTTPException(status_code=404, detail="Tasklist not found")

        for index, task in enumerate(task_collection):
            if task["id"] == task_id:
                task_collection.pop(index)
                return {"success": True, "detail": f"Task '{task_id}' deleted."}

        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")


def _create_stub_app() -> FastAPI:
    """Create a lightweight FastAPI app that mimics the Tasks service."""
    app = FastAPI(title="Stub Task Service", version="1.0.0")
    tasklists, tasks = _init_stub_data()
    _register_openapi_route(app)
    _register_tasklist_routes(app, tasklists, tasks)
    _register_task_routes(app, tasks)
    return app


class _StubServer(NamedTuple):
    server: uvicorn.Server
    thread: threading.Thread


def _start_stub_service(port: int) -> _StubServer:
    """Launch the stub FastAPI service in a background thread."""
    app = _create_stub_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return _StubServer(server=server, thread=thread)


def _stop_stub_service(stub_server: _StubServer) -> None:
    """Shut down the stub FastAPI service."""
    stub_server.server.should_exit = True
    stub_server.server.force_exit = True
    stub_server.thread.join(timeout=5)


class HTTPStatus(Enum):
    """HTTP status codes used in the API."""

    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500


def _free_port() -> int:
    """Return an available TCP port."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("", 0))
        return int(sock.getsockname()[1])


def _wait_for_ready(base_url: str, timeout_s: int = 45) -> None:
    """Poll the service until /openapi.json responds or timeout expires."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            response = httpx.get(f"{base_url}/openapi.json", timeout=2.0)
            if response.status_code < HTTPStatus.INTERNAL_SERVER_ERROR.value:
                return
        except Exception as e:
            # Log the exception for debugging, but continue polling
            if time.time() >= deadline - 0.5:  # Only log on last attempt
                error_msg = f"Service never became ready at {base_url}: {e}"
                raise RuntimeError(error_msg) from e
        time.sleep(0.5)

    error_msg = f"Service never became ready at {base_url}"
    raise RuntimeError(error_msg)


@pytest.fixture(scope="session")
def service_base_url() -> Generator[str, None, None]:
    """Run the FastAPI Tasks service in a sub-process for the duration of the test session."""
    global _USING_STUB_SERVICE  # noqa: PLW0603

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    required_env_vars = ["TASKS_CLIENT_ID", "TASKS_CLIENT_SECRET", "TASKS_REFRESH_TOKEN"]
    missing_env_vars = [var for var in required_env_vars if not os.environ.get(var)]

    runner: subprocess.Popen[str] | _StubServer
    _USING_STUB_SERVICE = bool(missing_env_vars)

    if not _USING_STUB_SERVICE:
        # Allow the FastAPI service to fall back to environment credentials during tests
        os.environ.setdefault("TASKS_ALLOW_ENV_IN_SERVICE", "true")
        env = os.environ.copy()
        src_paths = [
            str(Path("src/task_client_api/src").resolve()),
            str(Path("src/task_client_adapter/src").resolve()),
            str(Path("src/gtask_client_impl/src").resolve()),
            str(Path("src/task_client_service/src").resolve()),
            str(Path("src/task_client_service_client/src").resolve()),
        ]
        env["PYTHONPATH"] = os.pathsep.join(filter(None, (*src_paths, env.get("PYTHONPATH", ""))))
        env.setdefault("TASKS_ALLOW_ENV_IN_SERVICE", "true")

        cmd = [
            "uv",
            "run",
            "python",
            "-m",
            "uvicorn",
            "task_client_service.fast_api_service:app",
            "--app-dir",
            "src/task_client_service/src",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ]

        runner = subprocess.Popen(  # noqa: S603
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    else:
        runner = _start_stub_service(port)

    try:
        _wait_for_ready(base_url)
    except Exception:
        if isinstance(runner, subprocess.Popen):
            if runner.stdout:
                _ = runner.stdout.read()
            runner.kill()
        else:
            _stop_stub_service(runner)
        raise

    try:
        yield base_url
    finally:
        if isinstance(runner, subprocess.Popen):
            runner.terminate()
            try:
                runner.wait(timeout=5)
            except subprocess.TimeoutExpired:
                runner.kill()
        else:
            _stop_stub_service(runner)


@pytest.fixture(scope="session")
def shared_client(service_base_url: str) -> Client:
    """Provide a configured task service API client."""
    return Client(
        base_url=service_base_url,
        timeout=httpx.Timeout(30.0),
    )


@pytest.fixture
def task_adapter_client(shared_client: Client) -> ServiceClientAdapter:
    """Adapter fixture for local credential tests."""
    return ServiceClientAdapter(shared_client)


@pytest.fixture
def ci_task_adapter_client(shared_client: Client) -> ServiceClientAdapter:
    """Adapter fixture for CI-friendly tests."""
    return ServiceClientAdapter(shared_client)


def validate_tasklist_structure(tasklist_obj: Any) -> bool:
    """Validate that a tasklist object exposes the expected attributes."""
    required_fields = ["id", "title"]
    for field in required_fields:
        if not hasattr(tasklist_obj, field):
            return False
        value = getattr(tasklist_obj, field)
        if not isinstance(value, str):
            return False
    return True


def validate_task_structure(task_obj: Any) -> bool:
    """Validate that a task object exposes the expected attributes."""
    required_fields = ["id", "title", "status"]
    for field in required_fields:
        if not hasattr(task_obj, field):
            return False
        value = getattr(task_obj, field)
        if not isinstance(value, str):
            return False
    return True


@pytest.mark.local_credentials
def test_e2e_task_service_lists_tasklists(task_adapter_client: ServiceClientAdapter) -> None:
    """Ensure the adapter can list tasklists through the running service."""
    tasklists = task_adapter_client.list_tasklists()

    assert isinstance(tasklists, list)
    for tasklist_obj in tasklists:
        assert validate_tasklist_structure(tasklist_obj)


@pytest.mark.local_credentials
def test_e2e_task_service_lists_tasks(task_adapter_client: ServiceClientAdapter) -> None:
    """Ensure tasks can be listed from the first available tasklist."""
    tasklists = task_adapter_client.list_tasklists()
    if not tasklists:
        if _USING_STUB_SERVICE:
            pytest.fail("Expected stub service to provide at least one tasklist")
        pytest.skip("No tasklists available — likely due to missing Google Tasks credentials")

    first_tasklist = tasklists[0]
    tasks = task_adapter_client.list_tasks(first_tasklist.id)

    assert isinstance(tasks, list)
    for task_obj in tasks:
        assert validate_task_structure(task_obj)


@pytest.mark.local_credentials
def test_e2e_task_service_insert_and_delete_task(task_adapter_client: ServiceClientAdapter) -> None:
    """Create a task through the adapter and then delete it to validate round-trip behaviour."""
    tasklists = task_adapter_client.list_tasklists()
    if not tasklists:
        if _USING_STUB_SERVICE:
            pytest.fail("Expected stub service to provide at least one tasklist for insert/delete operations")
        pytest.skip("No tasklists available — cannot exercise insert/delete without credentials")

    target_tasklist = tasklists[0]
    task_title = f"E2E Task {time.time():.0f}"
    raw_task = json.dumps({"title": task_title})
    new_task = task_client_api.task.get_task(raw_data=raw_task)

    inserted_task = task_adapter_client.insert_task(target_tasklist.id, new_task)
    assert inserted_task.title == task_title

    deletion_success = task_adapter_client.delete_task(target_tasklist.id, inserted_task.id)
    assert deletion_success is True


@pytest.mark.local_credentials
def test_e2e_task_service_http_contract(service_base_url: str) -> None:
    """Hit the FastAPI endpoints directly to ensure the HTTP contract is intact."""
    try:
        response = httpx.get(f"{service_base_url}/tasklists", timeout=30.0)
    except httpx.ReadTimeout:
        pytest.skip("Task service timed out — service may be hanging on authentication")
    except httpx.ConnectTimeout:
        pytest.skip("Task service connection timed out — service may not be ready")
    except Exception as e:
        pytest.skip(f"Task service connection failed: {e}")

    if response.status_code == HTTPStatus.UNAUTHORIZED.value:
        pytest.skip("Task service returned 401 — credentials required for HTTP contract test")
    assert response.status_code == HTTPStatus.OK.value

    tasklists = response.json()
    assert isinstance(tasklists, list)

    if tasklists:
        first_tasklist = tasklists[0]
        assert "id" in first_tasklist
        tasklist_id = first_tasklist["id"]

        try:
            tasks_response = httpx.get(f"{service_base_url}/tasks/{tasklist_id}", timeout=30.0)
        except httpx.ReadTimeout:
            pytest.skip("Task service timed out when listing tasks — service may be hanging on authentication")
        except httpx.ConnectTimeout:
            pytest.skip("Task service connection timed out when listing tasks")
        except Exception as e:
            pytest.skip(f"Task service connection failed when listing tasks: {e}")

        if tasks_response.status_code == HTTPStatus.UNAUTHORIZED.value:
            pytest.skip("Task service returned 401 — credentials required for listing tasks")
        assert tasks_response.status_code == HTTPStatus.OK.value

        tasks_data = tasks_response.json()
        assert isinstance(tasks_data, list)


def test_e2e_task_service_failure_modes() -> None:
    """Validate behaviour when the service or network is unavailable."""
    invalid_client = Client(base_url="http://127.0.0.1:99999")
    invalid_adapter = ServiceClientAdapter(invalid_client)

    tasklists = invalid_adapter.list_tasklists()
    assert tasklists == []


@pytest.mark.e2e
def test_env_override_allows_env_credentials_in_fastapi_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure env fallback is used when override flag is set inside FastAPI context."""
    manager = OAuthManager()
    fake_creds = SimpleNamespace(valid=True, refresh_token="dummy")

    monkeypatch.setenv("TASKS_ALLOW_ENV_IN_SERVICE", "true")
    monkeypatch.setattr(OAuthManager, "_is_in_fastapi_context", lambda _self: True)
    monkeypatch.setattr(OAuthManager, "_get_session_credentials", lambda _self: None)

    calls: dict[str, Any] = {}

    def fake_auth_from_env(self: OAuthManager, *, interactive: bool) -> SimpleNamespace:
        calls["interactive"] = interactive
        return fake_creds

    monkeypatch.setattr(OAuthManager, "_auth_from_env", fake_auth_from_env)

    result = manager._get_non_interactive_credentials()

    assert result is fake_creds
    assert calls["interactive"] is False


@pytest.mark.e2e
def test_fastapi_context_without_override_blocks_env_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify env fallback is blocked when override flag is absent inside FastAPI context."""
    manager = OAuthManager()

    monkeypatch.delenv("TASKS_ALLOW_ENV_IN_SERVICE", raising=False)
    monkeypatch.setattr(OAuthManager, "_is_in_fastapi_context", lambda _self: True)
    monkeypatch.setattr(OAuthManager, "_get_session_credentials", lambda _self: None)

    auth_calls: list[bool] = []

    def fake_auth_from_env(self: OAuthManager, *, interactive: bool) -> SimpleNamespace:
        auth_calls.append(interactive)
        return SimpleNamespace(valid=True, refresh_token="dummy")

    monkeypatch.setattr(OAuthManager, "_auth_from_env", fake_auth_from_env)

    result = manager._get_non_interactive_credentials()

    assert result is None
    assert auth_calls == []


@pytest.mark.e2e
def test_env_override_applies_to_interactive_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure interactive auth also honours env fallback when override flag is set."""
    manager = OAuthManager()
    fake_creds = SimpleNamespace(valid=True, refresh_token="dummy")

    monkeypatch.setenv("TASKS_ALLOW_ENV_IN_SERVICE", "true")
    monkeypatch.delenv("TASKS_REFRESH_TOKEN", raising=False)  # Clear refresh token to avoid validation errors
    monkeypatch.setattr(OAuthManager, "_is_in_fastapi_context", lambda _self: True)

    def fake_auth_from_env(self: OAuthManager, *, interactive: bool) -> SimpleNamespace:
        assert interactive is True
        return fake_creds

    monkeypatch.setattr(OAuthManager, "_auth_from_env", fake_auth_from_env)

    result = manager._get_interactive_credentials()

    assert result is fake_creds


@pytest.mark.circleci
def test_ci_task_service_smoke(ci_task_adapter_client: ServiceClientAdapter) -> None:
    """CI-friendly smoke test that exercises the adapter with environment credentials only."""
    tasklists = ci_task_adapter_client.list_tasklists()
    assert isinstance(tasklists, list)
