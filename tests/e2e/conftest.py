"""Pytest configuration and fixtures for e2e tests.

This module provides fixtures to start and stop the main service
before running e2e tests.
"""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import time
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest
from dotenv import load_dotenv

if TYPE_CHECKING:
    from collections.abc import Generator

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# HTTP status code threshold for service readiness
HTTP_SERVER_ERROR_THRESHOLD = 500


def _free_port() -> int:
    """Return an available TCP port."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("", 0))
        return int(sock.getsockname()[1])


def _wait_for_service_ready(port: int, timeout_s: int = 45) -> None:
    """Poll the service until health check responds or timeout expires.

    Args:
        port: Port number the service is running on.
        timeout_s: Maximum time to wait in seconds.

    Raises:
        RuntimeError: If service doesn't become ready within timeout.

    """
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        try:
            # Try health check endpoint first, then root
            for endpoint in ["/health", "/"]:
                try:
                    response = httpx.get(f"{base_url}{endpoint}", timeout=2.0)
                    if response.status_code < HTTP_SERVER_ERROR_THRESHOLD:  # Any non-5xx is considered ready
                        return
                except httpx.RequestError:
                    continue
        except (httpx.RequestError, httpx.TimeoutException) as e:
            # Log the exception for debugging, but continue polling
            if time.time() >= deadline - 0.5:  # Only log on last attempt
                error_msg = f"Service never became ready at {base_url}: {e}"
                raise RuntimeError(error_msg) from e
        time.sleep(0.5)

    error_msg = f"Service never became ready at {base_url}"
    raise RuntimeError(error_msg)


@pytest.fixture(scope="session")
def main_service() -> Generator[subprocess.Popen[str], None, None]:
    """Start the main service in a subprocess for the duration of the test session.

    The service is started before tests run and stopped after all tests complete.
    """
    # Get a free port for the health check server
    port = _free_port()

    # Set up environment variables
    env = os.environ.copy()

    # Set the PORT environment variable for the health check server
    env["PORT"] = str(port)

    # Set up PYTHONPATH to include all necessary source paths
    src_paths = [
        str(Path("src/main_service/src").resolve()),
        str(Path("src/chat_api/src").resolve()),
        str(Path("src/chat_client_impl/src").resolve()),
        str(Path("src/discord_api/src").resolve()),
        str(Path("src/discord_client_impl/src").resolve()),
        str(Path("src/gtask_client_impl/src").resolve()),
        str(Path("src/task_client_api/src").resolve()),
        str(Path("src/tickets_api/src").resolve()),
        str(Path("src/tickets_client_impl/src").resolve()),
        str(Path("src/ai_api/src").resolve()),
        str(Path("src/openai_impl/src").resolve()),
    ]
    env["PYTHONPATH"] = os.pathsep.join(filter(None, (*src_paths, env.get("PYTHONPATH", ""))))

    # Command to start the main service
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "main_service.main",
    ]

    # Start the service process
    runner = subprocess.Popen(  # noqa: S603
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        # Give the process a moment to start up before checking health
        time.sleep(1)
        
        # Check if process died immediately
        returncode = runner.poll()
        if returncode is not None:
            # Process died, read output
            if runner.stdout:
                try:
                    output = runner.stdout.read()
                    if output:
                        error_msg = f"Service process exited immediately with code {returncode}. Output:\n{output}"
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)
                except (OSError, ValueError) as e:
                    logger.debug("Error reading service output: %s", e)
            raise RuntimeError(f"Service process exited immediately with code {returncode}")
        
        # Wait for the service to be ready
        _wait_for_service_ready(port, timeout_s=60)  # Increased timeout for slower CI environments
        # Give the service a moment to fully initialize (message tracking, etc.)
        time.sleep(2)
    except Exception as e:
        # If service fails to start, clean up and re-raise
        returncode = runner.poll()
        if runner.stdout:
            try:
                # Small delay to allow output to be buffered
                time.sleep(0.5)
                # Try to read available output (non-blocking read)
                output = ""
                try:
                    # Read in chunks to avoid blocking
                    while True:
                        chunk = runner.stdout.read(1024)
                        if not chunk:
                            break
                        output += chunk
                        if len(output) > 8192:  # Limit to 8KB
                            output += "\n... (truncated)"
                            break
                except Exception:
                    pass  # Ignore read errors
                if output:
                    logger.error("Service startup failed (exit code: %s). Output:\n%s", returncode, output)
            except Exception as read_error:
                logger.debug("Error reading service output: %s", read_error)
        if returncode is None:
            logger.warning("Service process still running (PID: %s) but not ready", runner.pid)
        runner.kill()
        raise RuntimeError(f"Failed to start service: {e}") from e

    try:
        yield runner
    finally:
        # Clean up: stop the service
        runner.terminate()
        try:
            runner.wait(timeout=5)
        except subprocess.TimeoutExpired:
            runner.kill()
            runner.wait()
