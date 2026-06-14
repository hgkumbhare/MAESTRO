import importlib
import sys
import types
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
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

project_management = importlib.import_module("src.tools_improved_smolagents.project_management")
company_directory = importlib.import_module("src.tools_improved_smolagents.company_directory")


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


def test_move_in_progress_tasks_to_in_review():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Prepare Q3 product launch plan",
                "assigned_to_email": "aisha.chen@atlas.com",
                "list_name": "In Progress",
                "due_date": "2023-09-01",
                "board": "Design",
            },
            {
                "task_id": "00000043",
                "task_name": "Final Launch",
                "assigned_to_email": "aisha.chen@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-09-01",
                "board": "Design",
            }
        ]
    )

    name = 'Aisha'
    emails = call_tool(company_directory.find_email_address, name)
    assert len(emails) == 1
    assert "aisha.chen@atlas.com" in emails
    assert "aisha.chen@example.com" not in emails

    email_id = str(emails[0])
    results = call_tool(project_management.search_tasks, assigned_to_email=email_id, list_name="In Progress" )
    assert len(results) == 1
    assert results[0]["task_id"] == "00000042"
    assert results[0]["assigned_to_email"] == "aisha.chen@atlas.com"

    update_message = call_tool(project_management.update_task, "00000042", "list_name", "In Review")
    assert update_message == "Task updated successfully."

    updated_task = project_management.PROJECT_TASKS.loc[
        project_management.PROJECT_TASKS["task_id"] == "00000042"
    ].iloc[0]
    assert updated_task["list_name"] == "In Review"


# Template: "Move all of {name}'s overdue tasks in the backlog to in progress"
def test_integration_move_all_overdue_backlog_tasks_to_in_progress():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Prepare Q3 product launch plan",
                "assigned_to_email": "aisha.chen@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-01-01",
                "board": "Design",
            },
            {
                "task_id": "00000043",
                "task_name": "Update onboarding flow",
                "assigned_to_email": "aisha.chen@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-01-10",
                "board": "Front end",
            },
            {
                "task_id": "00000044",
                "task_name": "Review marketing brief",
                "assigned_to_email": "carlos.rodriguez@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-01-01",
                "board": "Design",
            },
        ]
    )

    name = "Aisha"
    emails = call_tool(company_directory.find_email_address, name)
    assert len(emails) == 1
    returned_email = str(emails[0])

    results = call_tool(
        project_management.search_tasks,
        assigned_to_email=returned_email,
        list_name="Backlog",
        due_date="2023-01",
    )
    assert {task["task_id"] for task in results} == {"00000042", "00000043"}

    for task in results:
        update_message = call_tool(project_management.update_task, task["task_id"], "list_name", "In Progress")
        assert update_message == "Task updated successfully."

    updated_lists = project_management.PROJECT_TASKS.set_index("task_id")["list_name"].to_dict()
    assert updated_lists["00000042"] == "In Progress"
    assert updated_lists["00000043"] == "In Progress"
    assert updated_lists["00000044"] == "Backlog"


# Template: Move any of {name}'s tasks that are in review to completed"
def test_integration_move_any_review_tasks_to_completed():
    set_tasks(
        [
            {
                "task_id": "00000045",
                "task_name": "Finalize API contract",
                "assigned_to_email": "aisha.chen@atlas.com",
                "list_name": "In Review",
                "due_date": "2023-09-10",
                "board": "Back end",
            },
            {
                "task_id": "00000046",
                "task_name": "Proof content update",
                "assigned_to_email": "aisha.chen@atlas.com",
                "list_name": "In Progress",
                "due_date": "2023-09-15",
                "board": "Design",
            },
            {
                "task_id": "00000047",
                "task_name": "Send weekly status report",
                "assigned_to_email": "aisha.chen@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-09-20",
                "board": "Analytics",
            },
        ]
    )

    name = "Aisha"
    emails = call_tool(company_directory.find_email_address, name)
    assert len(emails) == 1
    returned_email = str(emails[0])

    review_tasks = call_tool(
        project_management.search_tasks,
        assigned_to_email=returned_email,
        list_name="In Review",
    )
    assert {task["task_id"] for task in review_tasks} == {"00000045"}

    for task in review_tasks:
        update_message = call_tool(project_management.update_task, task["task_id"], "list_name", "Completed")
        assert update_message == "Task updated successfully."

    updated_lists = project_management.PROJECT_TASKS.set_index("task_id")["list_name"].to_dict()
    assert updated_lists["00000045"] == "Completed"
    assert updated_lists["00000046"] == "In Progress"
    assert updated_lists["00000047"] == "Backlog"


# Template: "Move any of {name}'s tasks that are in review to completed"
def test_integration_move_any_review_tasks_to_completed_question():
    set_tasks(
        [
            {
                "task_id": "00000048",
                "task_name": "Validate deployment checklist",
                "assigned_to_email": "aisha.chen@atlas.com",
                "list_name": "In Progress",
                "due_date": "2023-09-25",
                "board": "Front end",
            },
            {
                "task_id": "00000049",
                "task_name": "Coordinate bug bash",
                "assigned_to_email": "aisha.chen@atlas.com",
                "list_name": "In Review",
                "due_date": "2023-09-22",
                "board": "Design",
            },
        ]
    )

    name = "Aisha"
    emails = call_tool(company_directory.find_email_address, name)
    assert len(emails) == 1
    returned_email = str(emails[0])

    review_tasks = call_tool(
        project_management.search_tasks,
        assigned_to_email=returned_email,
        list_name="In Review",
    )
    assert {task["task_id"] for task in review_tasks} == {"00000049"}

    for task in review_tasks:
        update_message = call_tool(project_management.update_task, task["task_id"], "list_name", "Completed")
        assert update_message == "Task updated successfully."

    updated_lists = project_management.PROJECT_TASKS.set_index("task_id")["list_name"].to_dict()
    assert updated_lists["00000048"] == "In Progress"
    assert updated_lists["00000049"] == "Completed"
