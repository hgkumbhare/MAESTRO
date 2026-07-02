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
customer_relationship_manager = importlib.import_module("src.tools_improved_smolagents.customer_relationship_manager")
analytics = importlib.import_module("src.tools_improved_smolagents.analytics")



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


def set_customers(records):
    """Replace the module-level CRM_DATA dataframe with the given customer records."""
    customer_relationship_manager.CRM_DATA = pd.DataFrame(records, dtype=str)


def set_analytics_data(records):
    """Replace the module-level analytics dataframe with the given records."""
    analytics.ANALYTICS_DATA = pd.DataFrame(records, dtype=str)
    analytics.ANALYTICS_DATA["user_engaged"] = analytics.ANALYTICS_DATA["user_engaged"] == "True"
    analytics.PLOTS_DATA = pd.DataFrame(columns=["file_path"])


# Start of integration tests for Project Management.
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
# End of integration tests for Project Management.

# Start of integration tests for CRM.
def test_integration_update_cameron_anderson_status_to_qualified_in_crm():
    set_customers(
        [
            {
                "customer_id": "00000001",
                "customer_name": "Cameron Anderson",
                "customer_email": "cameron.anderson@example.com",
                "customer_phone": "555-0183",
                "last_contact_date": "2024-05-10",
                "product_interest": "Software",
                "status": "Lead",
                "assigned_to_email": "grace.thompson@example.com",
                "notes": "Initial discovery call completed.",
                "follow_up_by": "2024-06-01",
            }
        ]
    )

    # Inputs: Update the status of Cameron Anderson to qualified in the CRM
    name = "Cameron Anderson"
    search_results = call_tool(
        customer_relationship_manager.search_customers,
        customer_name=name
    )
    assert len(search_results) == 1
    customer = search_results[0]
    assert customer["customer_name"] == name
    assert customer["status"] == "Lead"

    # Important: Do not call with parameters with empty string as argument like customer_email="".
    update_message = call_tool(
        customer_relationship_manager.update_customer,
        customer["customer_id"],
        "status",
        "Qualified",
    )
    assert update_message == "Customer updated successfully."

    updated_status = customer_relationship_manager.CRM_DATA.loc[
        customer_relationship_manager.CRM_DATA["customer_id"] == customer["customer_id"],
        "status",
    ].values[0]
    assert updated_status == "Qualified"


def test_integration_delete_customer_from_crm():
    set_customers(
        [
            {
                "customer_id": "00000196",
                "customer_name": "Kerry Robinson",
                "customer_email": "kerry.robinson@example.com",
                "customer_phone": "555-0199",
                "last_contact_date": "2024-04-15",
                "product_interest": "Consulting",
                "status": "Proposal",
                "assigned_to_email": "sofia.santos@example.com",
                "notes": "Quarterly follow-up scheduled.",
                "follow_up_by": "2024-06-10",
            }
        ]
    )

    # Inputs: Kerry Robinson is no longer a customer. Can you delete them from the CRM?
    name = "Kerry Robinson"
    search_results = call_tool(
        customer_relationship_manager.search_customers,
        customer_name=name,
    )
    assert len(search_results) == 1
    customer = search_results[0]
    assert customer["customer_name"] == name

    # Important: Do not call with parameters with empty string as argument like customer_email="".
    delete_message = call_tool(
        customer_relationship_manager.delete_customer,
        customer["customer_id"],
    )
    assert delete_message == "Customer deleted successfully."

    assert customer["customer_id"] not in customer_relationship_manager.CRM_DATA["customer_id"].values
    assert customer_relationship_manager.search_customers(customer_name=name) == []


def test_integration_reassign_specific_leads_in_crm():
    set_customers(
        [
            {
                "customer_id": "00000210",
                "customer_name": "customer 1",
                "customer_email": "customer_1@example.com",
                "customer_phone": "555-0170",
                "last_contact_date": "2024-04-01",
                "product_interest": "Services",
                "status": "Lead",
                "assigned_to_email": "lena.schmidt@atlas.com",
                "notes": "Interested in managed services.",
                "follow_up_by": "2024-06-05",
            },
            {
                "customer_id": "00000211",
                "customer_name": "customer 2",
                "customer_email": "customer_1@example.com",
                "customer_phone": "555-0171",
                "last_contact_date": "2024-04-02",
                "product_interest": "Services",
                "status": "Lead",
                "assigned_to_email": "lena.schmidt@atlas.com",
                "notes": "Looking for consulting support.",
                "follow_up_by": "2024-06-08",
            },
            {
                "customer_id": "00000212",
                "customer_name": "customer 3",
                "customer_email": "customer_3@example.com",
                "customer_phone": "555-0172",
                "last_contact_date": "2024-04-03",
                "product_interest": "Hardware",
                "status": "Lead",
                "assigned_to_email": "lena.schmidt@atlas.com",
                "notes": "Interested in a hardware bundle.",
                "follow_up_by": "2024-06-10",
            },
            {
                "customer_id": "00000213",
                "customer_name": "customer 4",
                "customer_email": "customer_4@example.com",
                "customer_phone": "555-0173",
                "last_contact_date": "2024-04-04",
                "product_interest": "Services",
                "status": "Qualified",
                "assigned_to_email": "lena.schmidt@atlas.com",
                "notes": "Already moved past lead stage.",
                "follow_up_by": "2024-06-12",
            },
        ]
    )

    # Inputs: We're moving all of Lena's leads that are interested in services to Sofia. Can you make that change in the CRM?
    source_name = "Lena"
    target_name = "Sofia"

    source_emails = call_tool(company_directory.find_email_address, source_name)
    assert len(source_emails) == 1
    source_email = str(source_emails[0])

    target_emails = call_tool(company_directory.find_email_address, target_name)
    assert len(target_emails) == 1
    target_email = str(target_emails[0])

    matching_customers = call_tool(
        customer_relationship_manager.search_customers,
        assigned_to_email=source_email,
        status="Lead",
        product_interest="Services",
    )
    assert {customer["customer_id"] for customer in matching_customers} == {"00000210", "00000211"}

    for customer in matching_customers:
        update_message = call_tool(
            customer_relationship_manager.update_customer,
            customer["customer_id"],
            "assigned_to_email",
            target_email,
        )
        assert update_message == "Customer updated successfully."

    updated_assignments = customer_relationship_manager.CRM_DATA.set_index("customer_id")["assigned_to_email"].to_dict()
    assert updated_assignments["00000210"] == target_email
    assert updated_assignments["00000211"] == target_email
    assert updated_assignments["00000212"] == source_email
    assert updated_assignments["00000213"] == source_email


def test_integration_move_proposal_consulting_customers_not_contacted_for_weeks_to_lost_in_crm():
    set_customers(
        [
            {
                "customer_id": "00000214",
                "customer_name": "Morgan Patel",
                "customer_email": "morgan.patel@example.com",
                "customer_phone": "555-0185",
                "last_contact_date": "2024-03-01",
                "product_interest": "Consulting",
                "status": "Proposal",
                "assigned_to_email": "emily.davis@example.com",
                "notes": "Waiting on proposal response.",
                "follow_up_by": "2024-06-01",
            },
            {
                "customer_id": "00000215",
                "customer_name": "Taylor Brooks",
                "customer_email": "taylor.brooks@example.com",
                "customer_phone": "555-0186",
                "last_contact_date": "2024-04-01",
                "product_interest": "Consulting",
                "status": "Proposal",
                "assigned_to_email": "emily.davis@example.com",
                "notes": "Proposal sent; no response in 6 weeks.",
                "follow_up_by": "2024-06-08",
            },
            {
                "customer_id": "00000216",
                "customer_name": "Jordan Lee",
                "customer_email": "jordan.lee@example.com",
                "customer_phone": "555-0187",
                "last_contact_date": "2024-05-01",
                "product_interest": "Consulting",
                "status": "Proposal",
                "assigned_to_email": "emily.davis@example.com",
                "notes": "Proposal recently sent.",
                "follow_up_by": "2024-06-20",
            },
            {
                "customer_id": "00000217",
                "customer_name": "Casey Nguyen",
                "customer_email": "casey.nguyen@example.com",
                "customer_phone": "555-0188",
                "last_contact_date": "2024-03-10",
                "product_interest": "Consulting",
                "status": "Qualified",
                "assigned_to_email": "emily.davis@example.com",
                "notes": "Already qualified, not a proposal lead.",
                "follow_up_by": "2024-06-12",
            },
            {
                "customer_id": "00000218",
                "customer_name": "Avery Morgan",
                "customer_email": "avery.morgan@example.com",
                "customer_phone": "555-0189",
                "last_contact_date": "2024-03-01",
                "product_interest": "Hardware",
                "status": "Proposal",
                "assigned_to_email": "emily.davis@example.com",
                "notes": "Consulting product not relevant.",
                "follow_up_by": "2024-06-15",
            },
        ]
    )

    # Inputs: Move all customers that haven't responded to a proposal for the consulting product in 6 weeks to lost in the CRM
    cutoff_date = "2024-04-13"
    eligible_customers = call_tool(
        customer_relationship_manager.search_customers,
        status="Proposal",
        product_interest="Consulting",
        last_contact_date_max=cutoff_date,
    )

    assert {customer["customer_id"] for customer in eligible_customers} == {"00000214", "00000215"}

    for customer in eligible_customers:
        update_message = call_tool(
            customer_relationship_manager.update_customer,
            customer["customer_id"],
            "status",
            "Lost",
        )
        assert update_message == "Customer updated successfully."

    status_by_id = customer_relationship_manager.CRM_DATA.set_index("customer_id")["status"].to_dict()
    assert status_by_id["00000214"] == "Lost"
    assert status_by_id["00000215"] == "Lost"
    assert status_by_id["00000216"] == "Proposal"
    assert status_by_id["00000217"] == "Qualified"
    assert status_by_id["00000218"] == "Proposal"


def test_integration_add_quinn_robinson_as_new_lead_assigned_to_raj():
    set_customers(
        [
            {
                "customer_id": "00000196",
                "customer_name": "Kerry Robinson",
                "customer_email": "kerry.robinson@example.com",
                "customer_phone": "555-0199",
                "last_contact_date": "2024-04-15",
                "product_interest": "Consulting",
                "status": "Proposal",
                "assigned_to_email": "sofia.santos@example.com",
                "notes": "Quarterly follow-up scheduled.",
                "follow_up_by": "2024-06-10",
            }
        ]
    )

    # Inputs: Add Quinn Robinson as a new lead in the crm and assign them to Raj
    customer_name = "Quinn Robinson"
    assigned_to_name = "Raj"

    # Tool calling
    assigned_to_emails = call_tool(company_directory.find_email_address, assigned_to_name)
    assert len(assigned_to_emails) == 1
    assigned_to_email = str(assigned_to_emails[0])

    # Important: Do not call with parameters with empty string as argument like customer_email="".
    customer_id = call_tool(
        customer_relationship_manager.add_customer,
        customer_name=customer_name,
        assigned_to_email=assigned_to_email,
        status="Lead",
    )
    assert customer_id is not None
    assert customer_id != ""

    # Verify the customer was added to CRM_DATA
    search_results = call_tool(
        customer_relationship_manager.search_customers,
        customer_name=customer_name,
    )
    assert len(search_results) == 1
    added_customer = search_results[0]
    assert added_customer["customer_name"] == customer_name
    assert added_customer["status"] == "Lead"
    assert added_customer["assigned_to_email"] == assigned_to_email
    assert added_customer["customer_id"] == customer_id



def test_integration_reassign_customers_in_crm():
    set_customers(
        [
            {
                "customer_id": "00000314",
                "customer_name": "Alex Jackson",
                "customer_email": "alex.jackson@example.com",
                "customer_phone": "555-0184",
                "last_contact_date": "2024-05-05",
                "product_interest": "Consulting",
                "status": "Qualified",
                "assigned_to_email": "sophia.lee@example.com",
                "notes": "Moving account ownership to Raj.",
                "follow_up_by": "2024-06-15",
            }
        ]
    )

    # Inputs: Raj is taking over Alex Jackson. Can you reassign them in the CRM?
    customer_name = "Alex Jackson"
    new_owner_name = "Raj"

    new_owner_emails = call_tool(company_directory.find_email_address, new_owner_name)
    assert len(new_owner_emails) == 1
    new_owner_email = str(new_owner_emails[0])

    search_results = call_tool(
        customer_relationship_manager.search_customers,
        customer_name=customer_name,
    )
    assert len(search_results) == 1
    customer = search_results[0]
    assert customer["customer_name"] == customer_name
    assert customer["assigned_to_email"] == "sophia.lee@example.com"

    update_message = call_tool(
        customer_relationship_manager.update_customer,
        customer["customer_id"],
        "assigned_to_email",
        new_owner_email,
    )
    assert update_message == "Customer updated successfully."

    updated_assignment = customer_relationship_manager.CRM_DATA.loc[
        customer_relationship_manager.CRM_DATA["customer_id"] == customer["customer_id"],
        "assigned_to_email",
    ].values[0]
    assert updated_assignment == new_owner_email
#  End of integration tests for CRM

# Start of integration tests for Analytics tool.
def test_integration_select_engaged_users_tool_for_engagement_request():
    # User message: "How many engaged users were there on 2023-11-01 and 2023-11-02?"
    # Expected tool call: analytics.engaged_users_count(time_min="2023-11-01", time_max="2023-11-02")
    # Expected output: {"2023-11-01": 1, "2023-11-02": 1}
    # Note: The model should select the engaged-users tool rather than the generic total-visits tool.
    set_analytics_data(
        [
            {"date_of_visit": "2023-11-01", "visitor_id": "100", "page_views": "2", "session_duration_seconds": "10.0", "traffic_source": "direct", "user_engaged": "True"},
            {"date_of_visit": "2023-11-02", "visitor_id": "101", "page_views": "3", "session_duration_seconds": "12.0", "traffic_source": "search engine", "user_engaged": "True"},
            {"date_of_visit": "2023-11-02", "visitor_id": "102", "page_views": "1", "session_duration_seconds": "9.0", "traffic_source": "referral", "user_engaged": "False"},
        ]
    )

    result = call_tool(analytics.engaged_users_count, time_min="2023-11-01", time_max="2023-11-02")
    assert result == {"2023-11-01": 1, "2023-11-02": 1}


def test_integration_use_total_visits_output_to_choose_histogram_date():
    # User message: "Create a histogram of the busiest day in November 2023."
    # Expected tool call: analytics.total_visits_count(time_min="2023-11-01", time_max="2023-11-30")
    # Expected output: {"2023-11-01": 2, "2023-11-02": 3, "2023-11-03": 1}
    # The returned value should be reused to choose the date for the follow-up plot.
    set_analytics_data(
        [
            {"date_of_visit": "2023-11-01", "visitor_id": "200", "page_views": "1", "session_duration_seconds": "8.0", "traffic_source": "direct", "user_engaged": "False"},
            {"date_of_visit": "2023-11-01", "visitor_id": "201", "page_views": "2", "session_duration_seconds": "10.0", "traffic_source": "search engine", "user_engaged": "True"},
            {"date_of_visit": "2023-11-02", "visitor_id": "202", "page_views": "3", "session_duration_seconds": "11.0", "traffic_source": "social media", "user_engaged": "True"},
            {"date_of_visit": "2023-11-02", "visitor_id": "203", "page_views": "4", "session_duration_seconds": "13.0", "traffic_source": "referral", "user_engaged": "True"},
            {"date_of_visit": "2023-11-02", "visitor_id": "204", "page_views": "2", "session_duration_seconds": "9.0", "traffic_source": "direct", "user_engaged": "False"},
            {"date_of_visit": "2023-11-03", "visitor_id": "205", "page_views": "1", "session_duration_seconds": "7.0", "traffic_source": "search engine", "user_engaged": "False"},
        ]
    )

    visit_counts = call_tool(analytics.total_visits_count, time_min="2023-11-01", time_max="2023-11-30")
    assert visit_counts == {"2023-11-01": 2, "2023-11-02": 3, "2023-11-03": 1}
    busiest_date = max(visit_counts, key=visit_counts.get)
    plot_path = call_tool(analytics.create_plot, busiest_date, busiest_date, "total_visits", "histogram")
    assert plot_path == "plots/2023-11-02_2023-11-02_total_visits_histogram.png"


def test_integration_use_average_session_duration_output_to_choose_line_chart_date():
    # User message: "Make a line chart of the day with the highest average session duration in November."
    # Expected tool call: analytics.get_average_session_duration(time_min="2023-11-01", time_max="2023-11-03")
    # Expected output: {"2023-11-01": 10.0, "2023-11-02": 15.5, "2023-11-03": 12.0}
    # The returned value should be reused to choose the follow-up plot date.
    set_analytics_data(
        [
            {"date_of_visit": "2023-11-01", "visitor_id": "300", "page_views": "2", "session_duration_seconds": "10.0", "traffic_source": "direct", "user_engaged": "False"},
            {"date_of_visit": "2023-11-02", "visitor_id": "301", "page_views": "5", "session_duration_seconds": "15.5", "traffic_source": "direct", "user_engaged": "True"},
            {"date_of_visit": "2023-11-02", "visitor_id": "302", "page_views": "2", "session_duration_seconds": "15.5", "traffic_source": "search engine", "user_engaged": "True"},
            {"date_of_visit": "2023-11-03", "visitor_id": "303", "page_views": "2", "session_duration_seconds": "12.0", "traffic_source": "referral", "user_engaged": "False"},
        ]
    )

    durations = call_tool(analytics.get_average_session_duration, time_min="2023-11-01", time_max="2023-11-03")
    assert durations == {"2023-11-01": 10.0, "2023-11-02": 15.5, "2023-11-03": 12.0}
    highest_duration_date = max(durations, key=durations.get)
    plot_path = call_tool(analytics.create_plot, highest_duration_date, highest_duration_date, "session_duration_seconds", "line")
    assert plot_path == "plots/2023-11-02_2023-11-02_session_duration_seconds_line.png"


def test_integration_clarify_when_plot_type_is_missing():
    # User message: "Create a chart of total visits from 2023-11-01 to 2023-11-03."
    # Expected behavior: ask for the missing plot type instead of guessing and calling create_plot.
    # Note: The model should request the missing required information before using any tool.
    set_analytics_data(
        [{"date_of_visit": "2023-11-01", "visitor_id": "400", "page_views": "1", "session_duration_seconds": "6.0", "traffic_source": "direct", "user_engaged": "False"}]
    )

    assert analytics.PLOTS_DATA.empty


def test_integration_request_authentication_before_calling_any_tool():
    # User message: "Create a chart of total visits from 2023-11-01 to 2023-11-03, but I have not authenticated yet."
    # Expected behavior: ask the user to authenticate first; do not call analytics.create_plot or any other analytics tool.
    # Note: The model should not invent an authentication token or proceed without consent.
    set_analytics_data(
        [{"date_of_visit": "2023-11-01", "visitor_id": "500", "page_views": "1", "session_duration_seconds": "7.0", "traffic_source": "direct", "user_engaged": "False"}]
    )

    assert analytics.PLOTS_DATA.empty


def test_integration_execute_immediately_when_all_required_inputs_are_available():
    # User message: "Plot total visits as a bar chart from 2023-11-01 to 2023-11-03."
    # Expected tool call: analytics.create_plot(time_min="2023-11-01", time_max="2023-11-03", value_to_plot="total_visits", plot_type="bar")
    # Expected output: "plots/2023-11-01_2023-11-03_total_visits_bar.png"
    # Note: Once the metric, dates, and plot type are all known, the model should execute immediately.
    set_analytics_data(
        [{"date_of_visit": "2023-11-01", "visitor_id": "600", "page_views": "1", "session_duration_seconds": "8.0", "traffic_source": "direct", "user_engaged": "False"}]
    )

    plot_path = call_tool(analytics.create_plot, "2023-11-01", "2023-11-03", "total_visits", "bar")
    assert plot_path == "plots/2023-11-01_2023-11-03_total_visits_bar.png"


def test_integration_do_not_invent_missing_dates_or_metrics():
    # User message: "Create a line chart of engaged users since yesterday."
    # Expected behavior: ask for the missing date in the exact format "YYYY-MM-DD" instead of inventing a value.
    # Note: The model should not invent arguments such as "2023-11-30" when the user did not provide them.
    set_analytics_data(
        [{"date_of_visit": "2023-11-01", "visitor_id": "700", "page_views": "3", "session_duration_seconds": "13.0", "traffic_source": "search engine", "user_engaged": "True"}]
    )

    assert analytics.PLOTS_DATA.empty

# End of integration tests for Analytics tool.