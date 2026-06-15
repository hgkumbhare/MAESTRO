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

    # Inputs: Move all of Aisha's tasks that are in progress to in review
    name = 'Aisha'
    current_list_name = "In Progress"
    updated_list_name = "In Review"

    # tool calling
    emails = call_tool(company_directory.find_email_address, name)
    assert len(emails) == 1
    assert "aisha.chen@atlas.com" in emails
    assert "aisha.chen@example.com" not in emails

    email_id = str(emails[0])
    results = call_tool(project_management.search_tasks, assigned_to_email=email_id, list_name=current_list_name )
    assert len(results) == 1
    assert results[0]["task_id"] == "00000042"
    assert results[0]["assigned_to_email"] == "aisha.chen@atlas.com"

    update_message = call_tool(project_management.update_task, "00000042", "list_name", updated_list_name)
    assert update_message == "Task updated successfully."

    updated_task = project_management.PROJECT_TASKS.loc[
        project_management.PROJECT_TASKS["task_id"] == "00000042"
    ].iloc[0]
    assert updated_task["list_name"] == updated_list_name


def test_integration_move_all_overdue_backlog_tasks_to_in_progress():
    set_tasks(
        [
            {
                "task_id": "00000042",
                "task_name": "Prepare Q3 product launch plan",
                "assigned_to_email": "aisha.chen@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-10-01",
                "board": "Design",
            },
            {
                "task_id": "00000043",
                "task_name": "Update onboarding flow",
                "assigned_to_email": "aisha.chen@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-11-30",
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

    # Inputs: "Move all of Aisha's overdue tasks in the backlog to in progress and today's date is 2023-11-30"
    name = 'Aisha'
    current_list_name = "Backlog"
    updated_list_name = "In Progress"
    today_date = "2023-11-30"

    # Tool calling
    emails = call_tool(company_directory.find_email_address, name)
    assert len(emails) == 1
    returned_email = str(emails[0])

    results = call_tool(
        project_management.search_tasks,
        assigned_to_email=returned_email,
        list_name=current_list_name
    )
    assert {task["task_id"] for task in results} == {"00000042", "00000043"}

    # Important: Get all tasks and update only if due date is older than today_date.
    for task in results:
        if task["due_date"] < today_date:
            update_message = call_tool(project_management.update_task, task["task_id"], "list_name", updated_list_name)
            assert update_message == "Task updated successfully."

    updated_lists = project_management.PROJECT_TASKS.set_index("task_id")["list_name"].to_dict()
    assert updated_lists["00000042"] == updated_list_name
    assert updated_lists["00000043"] == "Backlog"
    assert updated_lists["00000044"] == "Backlog"


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

    # Inputs: Move any of Aisha's tasks that are in review to completed"
    name = 'Aisha'
    current_list_name = "In Review"
    updated_list_name = "Completed"

    # Tool calling
    emails = call_tool(company_directory.find_email_address, name)
    assert len(emails) == 1
    returned_email = str(emails[0])

    review_tasks = call_tool(
        project_management.search_tasks,
        assigned_to_email=returned_email,
        list_name=current_list_name,
    )
    assert {task["task_id"] for task in review_tasks} == {"00000045"}

    for task in review_tasks:
        update_message = call_tool(project_management.update_task, task["task_id"], "list_name", updated_list_name)
        assert update_message == "Task updated successfully."

    updated_lists = project_management.PROJECT_TASKS.set_index("task_id")["list_name"].to_dict()
    assert updated_lists["00000045"] == updated_list_name
    assert updated_lists["00000046"] == "In Progress"
    assert updated_lists["00000047"] == "Backlog"


def test_integration_reassign_yukis_in_progress_tasks_to_carlos():
    set_tasks(
        [
            {
                "task_id": "00000048",
                "task_name": "Fix login bug",
                "assigned_to_email": "yuki.tanaka@atlas.com",
                "list_name": "In Progress",
                "due_date": "2023-10-15",
                "board": "Back end",
            },
            {
                "task_id": "00000049",
                "task_name": "Draft release notes",
                "assigned_to_email": "yuki.tanaka@atlas.com",
                "list_name": "In Progress",
                "due_date": "2023-10-20",
                "board": "Design",
            },
            {
                "task_id": "00000050",
                "task_name": "Organize team retro",
                "assigned_to_email": "yuki.tanaka@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-11-01",
                "board": "Analytics",
            },
            {
                "task_id": "00000055",
                "task_name": "Review sprint goals",
                "assigned_to_email": "carlos.rodriguez@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-10-30",
                "board": "Design",
            },
        ]
    )

    # Inputs: "reassign yuki's in progress tasks to carlos."
    name = "Yuki"

    # Tool calling
    yuki_emails = call_tool(company_directory.find_email_address, name)
    assert len(yuki_emails) == 1
    yuki_email = str(yuki_emails[0])

    carlos_emails = call_tool(company_directory.find_email_address, "Carlos")
    assert len(carlos_emails) == 1
    carlos_email = str(carlos_emails[0])

    in_progress_tasks = call_tool(
        project_management.search_tasks,
        assigned_to_email=yuki_email,
        list_name="In Progress",
    )
    assert {task["task_id"] for task in in_progress_tasks} == {"00000048", "00000049"}

    for task in in_progress_tasks:
        result = call_tool(project_management.update_task, task["task_id"], "assigned_to_email", carlos_email)
        assert result == "Task updated successfully."

    updated_assignees = project_management.PROJECT_TASKS.set_index("task_id")["assigned_to_email"].to_dict()
    assert updated_assignees["00000048"] == carlos_email
    assert updated_assignees["00000049"] == carlos_email
    assert updated_assignees["00000050"] == "yuki.tanaka@atlas.com"


def test_integration_move_unfinished_tasks_to_backlog():
    set_tasks(
        [
            {
                "task_id": "00000051",
                "task_name": "Complete user research summary",
                "assigned_to_email": "chenwei.zhang@atlas.com",
                "list_name": "In Progress",
                "due_date": "2023-10-05",
                "board": "Design",
            },
            {
                "task_id": "00000052",
                "task_name": "Update onboarding docs",
                "assigned_to_email": "chenwei.zhang@atlas.com",
                "list_name": "In Review",
                "due_date": "2023-10-07",
                "board": "Front end",
            },
            {
                "task_id": "00000053",
                "task_name": "Plan Q4 roadmap",
                "assigned_to_email": "chenwei.zhang@atlas.com",
                "list_name": "Backlog",
                "due_date": "2023-11-01",
                "board": "Analytics",
            },
            {
                "task_id": "00000054",
                "task_name": "Submit budget request",
                "assigned_to_email": "chenwei.zhang@atlas.com",
                "list_name": "Completed",
                "due_date": "2023-09-30",
                "board": "Back end",
            },
        ]
    )

    # Inputs: "can you move all of chenwei's unfinished tasks to the backlog?"
    name = "Chenwei"

    # Tool calling
    emails = call_tool(company_directory.find_email_address, name)
    assert len(emails) == 1
    email = str(emails[0])

    # Important: Unfinished tasks means in progress tasks only.
    # In review tasks are not unfinished tasks.
    all_tasks = call_tool(project_management.search_tasks, assigned_to_email=email, list_name="In progress")
    assert {task["task_id"] for task in all_tasks} == {"00000051"}

    for task in all_tasks:
        result = call_tool(project_management.update_task, task["task_id"], "list_name", "Backlog")
        assert result == "Task updated successfully."

    updated_lists = project_management.PROJECT_TASKS.set_index("task_id")["list_name"].to_dict()
    assert updated_lists["00000051"] == "Backlog"
    assert updated_lists["00000052"] == "In Review"
    assert updated_lists["00000053"] == "Backlog"
    assert updated_lists["00000054"] == "Completed"


