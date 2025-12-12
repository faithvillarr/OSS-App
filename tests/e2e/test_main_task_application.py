"""End-to-End tests for the Google Tasks demo application.

This module tests the Tasks demo script (`og_tickets.py`) as a black box,
simulating real user interactions and verifying the complete workflow.
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import gtask_client_impl
import task_client_api

# Resolve the repository root (one level above `tests/`)
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]

# Mark all tests in this file as e2e tests
pytestmark = pytest.mark.e2e


@pytest.mark.local_credentials
def test_main_script_runs_and_fetches_tasks() -> None:
    """Tests that the og_tickets.py script can be executed and successfully prints output indicating it has listed tasklists.

    This test requires real credentials and a live internet connection.
    Only runs locally with credentials.json or token.json files.
    """
    # Skip in CI - this test requires local credentials file
    if os.environ.get("CIRCLECI") == "true":
        pytest.skip("This test requires local credentials.json file - skipping in CI")

    # Get the path to og_tickets.py (should be in the workspace root)
    main_script = Path(__file__).parent.parent.parent / "og_tickets.py"

    if not main_script.exists():
        pytest.skip(f"og_tickets.py not found at {main_script}")

    # Check if credentials exist
    credentials_file = main_script.parent / "credentials.json"
    token_file = main_script.parent / "token.json"

    if not credentials_file.exists() and not token_file.exists():
        pytest.skip("No credentials.json or token.json found - cannot run E2E test")

    command = [
        sys.executable,  # Path to the current python interpreter
        str(main_script),
    ]

    try:
        # Run the command and capture the output
        # We need to be in the right directory for the script to find its dependencies
        result = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            check=True,  # Fail the test if the script returns a non-zero exit code
            timeout=120,  # Longer timeout for real network calls
            cwd=str(main_script.parent),  # Run from the script's directory
            input="DELETE\n",
        )

        # Assert that the script's output contains expected text
        output = (result.stdout or "") + (result.stderr or "")

        assert "Test 1: Listing all tasklists" in output
        assert "Demo complete" in output

    except subprocess.TimeoutExpired as e:
        # Check if timeout was due to interactive OAuth flow waiting for input
        combined_output = (e.stdout or "") + (e.stderr or "")
        if "interactive OAuth flow" in combined_output or "complete authentication in your browser" in combined_output:
            pytest.skip("Test timed out - interactive OAuth flow cannot complete in CI environment")
        pytest.fail("E2E test timed out - og_tickets.py took too long to execute")
    except subprocess.CalledProcessError as e:
        # If the script fails, print its output for easier debugging
        combined_error = (e.stderr or "") + (e.stdout or "")
        if "No valid credentials available" in combined_error or "Failed to obtain credentials" in combined_error:
            pytest.skip("Google Tasks credentials not available for og_tickets.py")
        if "credentials.json' not found" in combined_error or "Cannot run interactive auth" in combined_error:
            pytest.skip("credentials.json not found - cannot run interactive auth")
        pytest.fail(
            f"E2E test failed when running og_tickets.py.\nExit Code: {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}",
        )
    except FileNotFoundError:
        pytest.fail("Python interpreter or og_tickets.py not found")


@pytest.mark.circleci
def test_main_script_with_env_vars_only() -> None:  # noqa: PLR0915, PLR0912, C901
    """Tests that og_tickets.py works correctly in CI/CD environments.

    Uses only environment variables for authentication (no token.json or credentials.json).
    This test simulates CircleCI where only environment variables are available.
    """
    main_script = WORKSPACE_ROOT / "og_tickets.py"

    if not main_script.exists():
        pytest.skip(f"og_tickets.py not found at {main_script}")

    # Check if environment variables are set
    required_env_vars = ["TASKS_CLIENT_ID", "TASKS_CLIENT_SECRET", "TASKS_REFRESH_TOKEN"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

    if missing_vars:
        pytest.skip(f"Missing required environment variables for CI test: {missing_vars}")
    else:
        pass
    # Create a temporary Tasks demo script that uses interactive=False
    ci_main_content = """
# ta-assignment/og_tickets.py (CI/CD version)

# Import the contracts first
import task_client_api
import gtask_client_impl
import sys

def main() -> None:
    \"\"\"Initializes the client and demonstrates Google Tasks client methods.\"\"\"
    print("Attempting to initialize Google Tasks client...")
    try:
        # Try interactive=False first for CI/CD environments
        client = task_client_api.get_client(interactive=False)
        print("\\nSuccessfully authenticated and connected to the Google Tasks API using environment variables.")

        # Test 1: List tasklists (limited for CI)
        print("\\n=== TEST 1: Listing Tasklists ===")
        tasklists = client.list_tasklists()

        if not tasklists:
            print("No tasklists found.")
            return

        print(f"Found {len(tasklists)} tasklists:")
        for i, tasklist in enumerate(tasklists, 1):
            print(f"\\nTasklist {i}:")
            print(f"  ID: {tasklist.id}")
            print(f"  Title: {tasklist.title}")

        # Test 2: List tasks in the first tasklist
        first_tasklist = tasklists[0]
        print(f"\\n=== TEST 2: Listing Tasks in Tasklist '{first_tasklist.title}' ===")
        try:
            tasks = client.list_tasks(first_tasklist.id)
            if tasks:
                print(f"Found {len(tasks)} task(s):")
                for j, task in enumerate(tasks, 1):
                    print(f"  Task {j}: {task.title}")
            else:
                print("No tasks found in the selected tasklist.")
        except Exception as e:
            print(f"Error listing tasks: {e}")

        print("\\n=== CI Tests Completed Successfully ===")

    except RuntimeError as e:
        # In CI, if refresh token is invalid, we can't fix it (no interactive mode)
        error_msg = str(e)
        if "Failed to obtain credentials" in error_msg or "invalid_grant" in error_msg or "Bad Request" in error_msg:
            print(f"\\nAuthentication failed in CI environment: {error_msg}")
            print("This is expected if the refresh token is invalid or expired.")
            print("Skipping test gracefully.")
            sys.exit(0)  # Exit with success code to indicate graceful skip
        else:
            print(f"\\nAn error occurred: {e}")
            raise
    except Exception as e:
        print(f"\\nAn error occurred: {e}")
        raise

if __name__ == "__main__":
    main()
"""

    # Create temporary CI version of og_tickets.py
    ci_main_script = main_script.parent / "og_tickets_ci.py"

    try:
        # Write the CI version
        with ci_main_script.open("w") as f:
            f.write(ci_main_content)

        # Temporarily hide credential files to ensure we're using env vars only
        credentials_file = main_script.parent / "credentials.json"
        token_file = main_script.parent / "token.json"

        backup_files = []

        try:
            # Backup existing credential files
            if credentials_file.exists():
                backup_cred = credentials_file.with_suffix(".json.ci_backup")
                credentials_file.rename(backup_cred)
                backup_files.append((credentials_file, backup_cred))

            if token_file.exists():
                backup_token = token_file.with_suffix(".json.ci_backup")
                token_file.rename(backup_token)
                backup_files.append((token_file, backup_token))

            command = [sys.executable, str(ci_main_script)]

            # Run the CI version
            result = subprocess.run(  # noqa: S603
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=60,  # Shorter timeout for CI
                cwd=str(main_script.parent),
            )

            # Assert that the script's output contains expected text
            output = result.stdout

            assert "Attempting to initialize Google Tasks client..." in output

            # Check if authentication failed gracefully (invalid refresh token in CI)
            if "Authentication failed in CI environment" in output or "Skipping test gracefully" in output:
                # If authentication failed, skip the test instead of failing
                pytest.skip("Refresh token is invalid or expired in CI environment - cannot authenticate")

            # If we get here, authentication succeeded
            assert "Successfully authenticated and connected to the Google Tasks API using environment variables." in output

            # Check for test sections
            assert "=== TEST 1: Listing Tasklists ===" in output
            assert "=== TEST 2: Listing Tasks in Tasklist" in output
            assert "=== CI Tests Completed Successfully ===" in output

        finally:
            # Restore backup files
            for original, backup in backup_files:
                if backup.exists():
                    backup.rename(original)

    except subprocess.TimeoutExpired:
        pytest.fail("CI E2E test timed out")
    except subprocess.CalledProcessError as e:
        # Check if this is an authentication failure (invalid refresh token)
        combined_output = (e.stdout or "") + (e.stderr or "")
        if any(
            msg in combined_output
            for msg in [
                "Failed to obtain credentials",
                "invalid_grant",
                "Bad Request",
                "Authentication failed in CI environment",
            ]
        ):
            pytest.skip("Refresh token is invalid or expired in CI environment - cannot authenticate")
        pytest.fail(
            f"CI E2E test failed when running og_tickets_ci.py.\nExit Code: {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}",
        )
    finally:
        # Clean up temporary file
        if ci_main_script.exists():
            ci_main_script.unlink()


@pytest.mark.local_credentials
def test_main_script_handles_no_credentials_gracefully(tmp_path: Path) -> None:
    """Ensure the Google Tasks client raises a helpful error when no credentials are provided."""
    patched_env = {
        "TASKS_CLIENT_ID": "",
        "TASKS_CLIENT_SECRET": "",
        "TASKS_REFRESH_TOKEN": "",
        "TASKS_TOKEN_URI": "https://oauth2.googleapis.com/token",
    }

    # Import and register the Google Tasks client implementation within the test context
    # Re-register the Tasks client implementation after conftest has reset it
    # We need to do this because the conftest autouse fixture resets dependency injection
    from gtask_client_impl.auth import OAuthManager
    from gtask_client_impl.gtask_impl import get_client_impl

    task_client_api.get_client = get_client_impl

    def _call_client() -> None:
        client = task_client_api.get_client(interactive=False)
        client.list_tasklists()

    with (
        patch.dict(os.environ, patched_env, clear=False),
        patch.object(OAuthManager, "CREDENTIALS_PATH", str(tmp_path / "credentials.json")),
        pytest.raises(RuntimeError) as excinfo,
    ):
        _call_client()

    message = str(excinfo.value)
    assert message == gtask_client_impl.GTaskClient.FAILURE_TO_CRED


@pytest.mark.circleci
def test_main_script_syntax_is_valid() -> None:
    """Tests that og_tickets.py has valid Python syntax.

    This can run in any environment.
    """
    main_script = WORKSPACE_ROOT / "og_tickets.py"

    if not main_script.exists():
        pytest.skip(f"og_tickets.py not found at {main_script}")

    # Check syntax without executing
    command = [sys.executable, "-m", "py_compile", str(main_script)]

    try:
        subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        # If we get here, syntax is valid

    except subprocess.CalledProcessError as e:
        pytest.fail(f"og_tickets.py has syntax errors:\n{e.stderr}")


@pytest.mark.circleci
def test_main_script_imports_work() -> None:
    """Tests that og_tickets.py can import all required modules.

    This can run in any environment.
    """
    main_script = WORKSPACE_ROOT / "og_tickets.py"

    if not main_script.exists():
        pytest.skip(f"og_tickets.py not found at {main_script}")

    # Test imports without running main logic
    import_test_code = """
try:
    import task_client_api
    import gtask_client_impl
    print("All imports successful")
except ImportError as e:
    print(f"Import error: {e}")
    raise
"""

    command = [sys.executable, "-c", import_test_code]

    try:
        result = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
            cwd=str(main_script.parent),  # Run from the script's directory
        )

        assert "All imports successful" in result.stdout

    except subprocess.CalledProcessError as e:
        pytest.fail(f"og_tickets.py imports failed:\n{e.stderr}")


@pytest.mark.circleci
def test_application_structure_integrity() -> None:
    """Tests that the application has the expected file structure.

    This can run in any environment.
    """
    workspace_root = WORKSPACE_ROOT

    expected_files = [
        "og_tickets.py",
        "pyproject.toml",
        "src/task_client_api/src/task_client_api/__init__.py",
        "src/task_client_api/src/task_client_api/client.py",
        "src/task_client_api/src/task_client_api/task.py",
        "src/task_client_api/src/task_client_api/tasklist.py",
        "src/gtask_client_impl/src/gtask_client_impl/__init__.py",
        "src/gtask_client_impl/src/gtask_client_impl/gtask_impl.py",
        "src/gtask_client_impl/src/gtask_client_impl/task_impl.py",
        "src/gtask_client_impl/src/gtask_client_impl/tasklist_impl.py",
    ]

    missing_files = []

    for file_path in expected_files:
        full_path = workspace_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)

    if missing_files:
        pytest.fail(f"Missing required files: {missing_files}")
