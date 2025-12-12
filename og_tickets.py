"""Main module for demonstrating the task client."""

import json
import logging
import os
from pathlib import Path

import gtask_client_impl  # noqa: F401
import task_client_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:  # noqa: PLR0912, PLR0915, C901 # Just a test script
    """Initialize the client and demonstrate all task client methods."""
    # In CI environments (like CircleCI), use non-interactive mode with environment variables
    # Otherwise, use interactive mode if credentials.json exists
    is_ci = os.environ.get("CIRCLECI") == "true"
    has_credentials = Path("credentials.json").exists()
    use_interactive = not is_ci and has_credentials

    # Now, get_client() returns a GTaskClient instance...
    client = task_client_api.get_client(interactive=use_interactive)

    # Test 1: List all tasklists
    logger.info("Test 1: Listing all tasklists...")
    tasklists = client.list_tasklists()
    logger.info("Found %d tasklist(s)", len(tasklists))

    # Test 1.5: Create a test tasklist if none exist, or test insert/delete functionality
    test_tasklist_for_operations = None
    if not tasklists:
        logger.info("No tasklists found. Creating a test tasklist...")
        try:
            # Create a minimal TaskList object with just a title
            tasklist_data = {"title": "Test Tasklist - Insert/Delete Demo"}
            raw_data = json.dumps(tasklist_data)
            # Create tasklist - the implementation should handle minimal data
            new_tasklist = task_client_api.tasklist.get_tasklist(raw_data=raw_data)
            # Insert the tasklist via service call
            inserted_tasklist = client.insert_tasklist(new_tasklist)
            logger.info(
                "Created test tasklist: '%s' (ID: %s)",
                inserted_tasklist.title,
                inserted_tasklist.id,
            )
            tasklists = [inserted_tasklist]
            test_tasklist_for_operations = inserted_tasklist
        except Exception as e:  # noqa: BLE001 # this is a test script. we don't need to handle exceptions.
            logger.info("Failed to create test tasklist: %s", e)
            logger.info("Skipping further tests - no tasklists available.")
            return
    else:
        # Test inserting and deleting a tasklist when tasklists already exist
        logger.info("\nTest 1.5: Testing insert_tasklist functionality...")
        try:
            tasklist_data = {"title": "Test Tasklist - Delete Me"}
            raw_data = json.dumps(tasklist_data)
            new_tasklist = task_client_api.tasklist.get_tasklist(raw_data=raw_data)
            inserted_tasklist = client.insert_tasklist(new_tasklist)
            logger.info(
                "Created test tasklist: '%s' (ID: %s)",
                inserted_tasklist.title,
                inserted_tasklist.id,
            )
            test_tasklist_for_operations = inserted_tasklist
        except Exception as e:  # noqa: BLE001 # this is a test script. we don't need to handle exceptions.
            logger.info("Failed to create test tasklist: %s", e)
            test_tasklist_for_operations = None

    # Display tasklists
    for i, tasklist in enumerate(tasklists, 1):
        logger.info("TaskList %d: %s (ID: %s)", i, tasklist.title, tasklist.id)

    # Test 2: Get tasks from the first tasklist
    test_tasklist = tasklists[0]
    logger.info("\nTest 2: Listing tasks from tasklist '%s'...", test_tasklist.title)
    tasks = client.list_tasks(test_tasklist.id)

    logger.info("Found %d task(s) in tasklist '%s'", len(tasks), test_tasklist.title)

    # Display tasks
    for i, task in enumerate(tasks, 1):
        status_emoji = "✓" if task.status == "completed" else "○"
        logger.info(
            "Task %d: %s %s (ID: %s)",
            i,
            status_emoji,
            task.title,
            task.id,
        )
        if task.notes:
            logger.info("  Notes: %s", task.notes[:50])
        if task.due:
            logger.info("  Due: %s", task.due)

    # Test 3: Create and store a task locally
    if test_tasklist:
        logger.info("\nTest 3: Creating and storing a new test task...")
        try:
            # Create a minimal Task object with just a title
            # We need raw_data to create a Task, so we'll use a minimal JSON structure
            task_data = {"title": "Test Task 101- Delete and Reinsert"}
            raw_data = json.dumps(task_data)

            # Create task with temporary ID (will be replaced after insert)
            # Calling the create task function associated with task object, NOT the service call
            new_task = task_client_api.task.get_task(raw_data=raw_data)

            # Insert the task via service call
            inserted_task = client.insert_task(test_tasklist.id, new_task)
            logger.info(
                "Created and stored task: '%s' (ID: %s)",
                inserted_task.title,
                inserted_task.id,
            )
            # Store the task locally for later operations
            stored_task = inserted_task
            stored_task_data = {
                "title": stored_task.title,
                "notes": stored_task.notes,
                "status": stored_task.status,
                "due": stored_task.due,
            }

            # Test 4: Delete the stored task
            logger.info("\nTest 4: Deleting the stored task...")
            deletion_success = client.delete_task(test_tasklist.id, stored_task.id)
            if deletion_success:
                logger.info(
                    "Task '%s' (ID: %s) deleted successfully.",
                    stored_task.title,
                    stored_task.id,
                )
            else:
                logger.info(
                    "Failed to delete task '%s' (ID: %s).",
                    stored_task.title,
                    stored_task.id,
                )

            # Test 5: Reinsert the task (only if deletion was successful)
            if deletion_success:
                logger.info("\nTest 5: Reinserting the deleted task...")
                try:
                    # Recreate the task object with the stored data
                    raw_data_reinsert = json.dumps(stored_task_data)
                    task_to_reinsert = task_client_api.task.get_task(raw_data=raw_data_reinsert)
                    # Reinsert the task
                    reinserted_task = client.insert_task(test_tasklist.id, task_to_reinsert)
                    logger.info(
                        "Reinserted task: '%s' (ID: %s)",
                        reinserted_task.title,
                        reinserted_task.id,
                    )
                except Exception as e:  # noqa: BLE001 # this is a test script. we don't need to handle exceptions.
                    logger.info("Failed to reinsert task: %s", e)
        except Exception as e:  # noqa: BLE001 # this is a test script. we don't need to handle exceptions.
            logger.info("Failed to create/store task: %s", e)
    else:
        logger.info("\nTest 3: Skipping task creation (no tasklist available)")

    # Test 6: Delete the test tasklist (if we created one)
    if test_tasklist_for_operations:
        logger.info("\nTest 6: Deleting the test tasklist...")
        logger.info(
            "Tasklist to delete: '%s' (ID: %s)",
            test_tasklist_for_operations.title,
            test_tasklist_for_operations.id,
        )
        try:
            user_input = input("Do you want to delete this tasklist? Type 'DELETE' to confirm: ").strip()
        except EOFError:
            # This means that CircleCI or another non-interactive environment is not going to actually delete anything
            logger.info(
                "Deletion skipped in non-interactive environment. Tasklist '%s' (ID: %s) was not deleted.",
                test_tasklist_for_operations.title,
                test_tasklist_for_operations.id,
            )
            user_input = ""

        if user_input == "DELETE":
            try:
                deletion_success = client.delete_tasklist(test_tasklist_for_operations.id)
                if deletion_success:
                    logger.info(
                        "Tasklist '%s' (ID: %s) deleted successfully.",
                        test_tasklist_for_operations.title,
                        test_tasklist_for_operations.id,
                    )
                else:
                    logger.info(
                        "Failed to delete tasklist '%s' (ID: %s).",
                        test_tasklist_for_operations.title,
                        test_tasklist_for_operations.id,
                    )
            except Exception as e:  # noqa: BLE001 # this is a test script. we don't need to handle exceptions.
                logger.info("Failed to delete tasklist: %s", e)
        else:
            logger.info(
                "Deletion cancelled. Tasklist '%s' (ID: %s) was not deleted.",
                test_tasklist_for_operations.title,
                test_tasklist_for_operations.id,
            )

    logger.info("\nDemo complete.")


if __name__ == "__main__":
    main()
