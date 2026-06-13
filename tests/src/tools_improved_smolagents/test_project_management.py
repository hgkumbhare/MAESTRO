import importlib
import sys
import types
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CURRENT_DIR = Path(__file__).resolve().parent
while str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Stub out smolagents so the @tool decorator is a no-op and the module imports
# without the real dependency. Must be registered before importing the module.
smolagents_stub = types.ModuleType("smolagents")
smolagents_stub.tool = lambda func: func
sys.modules["smolagents"] = smolagents_stub

import pandas as pd

project_management = importlib.import_module("src.tools_improved_smolagents.project_management")


def call_tool(tool_obj, *args, **kwargs):
    """Invoke a tool whether it's a plain function or a smolagents Tool object."""
    if hasattr(tool_obj, "func"):
        return tool_obj.func(*args, **kwargs)
    if hasattr(tool_obj, "forward"):
        return tool_obj.forward(*args, **kwargs)
    return tool_obj(*args, **kwargs)


def set_tasks(records):
    """Replace the module-level PROJECT_TASKS dataframe with the given records."""
    project_management.PROJECT_TASKS = pd.DataFrame(records, dtype=str)


# ---------------------------------------------------------------------------
# get_task_information_by_id
# ---------------------------------------------------------------------------


def test_get_task_information_by_id_returns_requested_field():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Refactor authentication module",
                "assigned_to_email": "sarah@atlas.com",
                "list_name": "In Progress",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )

    assert call_tool(project_management.get_task_information_by_id, "00000042", "task_name") == {
        "task_name": "Refactor authentication module"
    }
    assert call_tool(project_management.get_task_information_by_id, "00000042", "assigned_to_email") == {
        "assigned_to_email": "sarah@atlas.com"
    }


def test_get_task_information_by_id_missing_task_id():
    set_tasks([])
    assert call_tool(project_management.get_task_information_by_id) == "Task ID not provided."


def test_get_task_information_by_id_missing_field():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Refactor authentication module",
                "assigned_to_email": "sarah@atlas.com",
                "list_name": "In Progress",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )
    assert call_tool(project_management.get_task_information_by_id, "00000042") == "Field not provided."


def test_get_task_information_by_id_unknown_field():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Refactor authentication module",
                "assigned_to_email": "sarah@atlas.com",
                "list_name": "In Progress",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )
    assert call_tool(project_management.get_task_information_by_id, "00000042", "priority") == "Field not found."


def test_get_task_information_by_id_unknown_task():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Refactor authentication module",
                "assigned_to_email": "sarah@atlas.com",
                "list_name": "In Progress",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )
    assert call_tool(project_management.get_task_information_by_id, "00000999", "task_name") == "Task not found."


# ---------------------------------------------------------------------------
# search_tasks
# ---------------------------------------------------------------------------


def test_search_tasks_no_parameters():
    set_tasks([])
    assert call_tool(project_management.search_tasks) == "No search parameters provided."


def test_search_tasks_partial_case_insensitive_name():
    set_tasks(
        [
            {
                "task_id": "00000001",
                "task_name": "API integration",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-08-15",
                "board": "Back end",
            },
            {
                "task_id": "00000002",
                "task_name": "Update API docs",
                "assigned_to_email": "jordan@atlas.com",
                "list_name": "In Progress",
                "due_date": "2023-07-01",
                "board": "Design",
            },
            {
                "task_id": "00000003",
                "task_name": "Fix login bug",
                "assigned_to_email": "sarah@atlas.com",
                "list_name": "Completed",
                "due_date": "2023-06-20",
                "board": "Front end",
            },
        ]
    )

    results = call_tool(project_management.search_tasks, task_name="api")
    assert [task["task_id"] for task in results] == ["00000001", "00000002"]


def test_search_tasks_multiple_fields_are_anded():
    set_tasks(
        [
            {
                "task_id": "00000001",
                "task_name": "API integration",
                "assigned_to_email": "sarah@atlas.com",
                "list_name": "In Progress",
                "due_date": "2023-08-15",
                "board": "Back end",
            },
            {
                "task_id": "00000002",
                "task_name": "API cleanup",
                "assigned_to_email": "sarah@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-08-16",
                "board": "Back end",
            },
        ]
    )

    results = call_tool(
        project_management.search_tasks,
        assigned_to_email="sarah@atlas.com",
        list_name="In Progress",
    )
    assert len(results) == 1
    assert results[0]["task_id"] == "00000001"


def test_search_tasks_returns_full_records():
    record = {
        "task_id": "00000001",
        "task_name": "API integration",
        "assigned_to_email": "alex@atlas.com",
        "list_name": "Backlog",
        "due_date": "2023-08-15",
        "board": "Back end",
    }
    set_tasks([record])

    assert call_tool(project_management.search_tasks, board="Back end") == [record]


def test_search_tasks_no_matches_returns_empty_list():
    set_tasks(
        [
            {
                "task_id": "00000001",
                "task_name": "API integration",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-08-15",
                "board": "Back end",
            }
        ]
    )

    assert call_tool(project_management.search_tasks, task_name="nonexistent") == []


# ---------------------------------------------------------------------------
# create_task
# ---------------------------------------------------------------------------


def test_create_task_appends_and_returns_new_id_and_lowercases_email():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )

    new_id = call_tool(
        project_management.create_task,
        "Integrate payment gateway",
        "Alex@atlas.com",
        "Backlog",
        "2023-08-15",
        "Back end",
    )

    assert new_id == "00000043"
    new_task = project_management.PROJECT_TASKS[
        project_management.PROJECT_TASKS["task_id"] == new_id
    ].iloc[0]
    assert new_task["task_name"] == "Integrate payment gateway"
    assert new_task["assigned_to_email"] == "alex@atlas.com"
    assert new_task["board"] == "Back end"


def test_create_task_missing_details():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )
    assert (
        call_tool(project_management.create_task, "Task", "alex@atlas.com", "Backlog", "2023-08-15")
        == "Missing task details."
    )


def test_create_task_invalid_assignee():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )
    assert (
        call_tool(
            project_management.create_task,
            "New task",
            "stranger@atlas.com",
            "Backlog",
            "2023-08-15",
            "Back end",
        )
        == "Assignee email not valid. Please choose from the list of team members."
    )


def test_create_task_invalid_list_name():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )
    assert (
        call_tool(
            project_management.create_task,
            "New task",
            "alex@atlas.com",
            "Done",
            "2023-08-15",
            "Back end",
        )
        == "List not valid. Please choose from: 'Backlog', 'In Progress', 'In Review', 'Completed'."
    )


def test_create_task_invalid_board():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )
    assert (
        call_tool(
            project_management.create_task,
            "New task",
            "alex@atlas.com",
            "Backlog",
            "2023-08-15",
            "Mobile",
        )
        == "Board not valid. Please choose from: 'Back end', 'Front end', 'Design'."
    )


# ---------------------------------------------------------------------------
# delete_task
# ---------------------------------------------------------------------------


def test_delete_task_removes_existing_task():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )

    assert call_tool(project_management.delete_task, "00000042") == "Task deleted successfully."
    assert "00000042" not in project_management.PROJECT_TASKS["task_id"].values


def test_delete_task_missing_id():
    set_tasks([])
    assert call_tool(project_management.delete_task) == "Task ID not provided."


def test_delete_task_unknown_id():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )
    assert call_tool(project_management.delete_task, "00000999") == "Task not found."


# ---------------------------------------------------------------------------
# update_task
# ---------------------------------------------------------------------------


def test_update_task_changes_field():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )

    assert call_tool(project_management.update_task, "00000042", "list_name", "In Review") == "Task updated successfully."
    assert (
        project_management.PROJECT_TASKS.loc[
            project_management.PROJECT_TASKS["task_id"] == "00000042", "list_name"
        ].values[0]
        == "In Review"
    )


def test_update_task_normalizes_email():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )

    assert (
        call_tool(project_management.update_task, "00000042", "assigned_to_email", "Alex@atlas.com")
        == "Task updated successfully."
    )
    assert (
        project_management.PROJECT_TASKS.loc[
            project_management.PROJECT_TASKS["task_id"] == "00000042", "assigned_to_email"
        ].values[0]
        == "alex@atlas.com"
    )


def test_update_task_missing_parameters():
    set_tasks([])
    assert (
        call_tool(project_management.update_task, "00000042", "list_name")
        == "Task ID, field, or new value not provided."
    )


def test_update_task_invalid_board():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )
    assert (
        call_tool(project_management.update_task, "00000042", "board", "Mobile")
        == "Board not valid. Please choose from: 'Back end', 'Front end', 'Design'."
    )


def test_update_task_invalid_list_name():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )
    assert (
        call_tool(project_management.update_task, "00000042", "list_name", "Done")
        == "List not valid. Please choose from: 'Backlog', 'In Progress', 'In Review', 'Completed'."
    )


def test_update_task_invalid_assignee():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )
    assert (
        call_tool(project_management.update_task, "00000042", "assigned_to_email", "stranger@atlas.com")
        == "Assignee email not valid. Please choose from the list of team members."
    )


def test_update_task_unknown_field():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )
    assert call_tool(project_management.update_task, "00000042", "priority", "high") == "Field not valid."


def test_update_task_unknown_task():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Existing task",
                "assigned_to_email": "alex@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-07-15",
                "board": "Back end",
            }
        ]
    )
    assert call_tool(project_management.update_task, "00000999", "list_name", "In Review") == "Task not found."


# ---------------------------------------------------------------------------
# reset_state
# ---------------------------------------------------------------------------


def test_reset_state_reloads_from_csv():
    set_tasks([])
    project_management.reset_state()
    assert not project_management.PROJECT_TASKS.empty
    assert "task_id" in project_management.PROJECT_TASKS.columns
