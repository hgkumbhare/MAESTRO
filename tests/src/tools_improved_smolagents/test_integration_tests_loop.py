import os
import sys

import pandas as pd

# Ensure repository root is on sys.path so `src` package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Stub out smolagents so the @tool decorator is a no-op and modules import
# without the real dependency.
import types
smolagents_stub = types.ModuleType("smolagents")
smolagents_stub.tool = lambda func: func
sys.modules["smolagents"] = smolagents_stub

from src.tools_improved_smolagents import (
    analytics,
    calendar,
    email,
    project_management,
    customer_relationship_manager as crm,
    company_directory,
)

from src.tools_improved_smolagents.company_directory import find_email_address
from src.tools_improved_smolagents.calendar import (
    get_event_information_by_id,
    search_events,
    create_event,
    delete_event,
    update_event,
)
from src.tools_improved_smolagents.email import (
    get_email_information_by_id,
    search_emails,
    send_email,
    delete_email,
    forward_email,
    reply_email,
)
from src.tools_improved_smolagents.project_management import (
    get_task_information_by_id,
    search_tasks,
    create_task,
    delete_task,
    update_task,
)
from src.tools_improved_smolagents.customer_relationship_manager import (
    search_customers,
    update_customer,
    add_customer,
    delete_customer,
)
from src.tools_improved_smolagents.analytics import (
    get_visitor_information_by_id,
    create_plot,
    total_visits_count,
    engaged_users_count,
    traffic_source_count,
    get_average_session_duration,
)

def set_tasks(records):
    project_management.PROJECT_TASKS = pd.DataFrame(records, dtype=str)


def set_customers(records):
    crm.CRM_DATA = pd.DataFrame(records, dtype=str)


def set_analytics_data(records):
    analytics.ANALYTICS_DATA = pd.DataFrame(records, dtype=str)
    analytics.ANALYTICS_DATA["user_engaged"] = analytics.ANALYTICS_DATA["user_engaged"] == "True"
    analytics.PLOTS_DATA = pd.DataFrame(columns=["file_path"])


def set_events(records):
    calendar.CALENDAR_EVENTS = pd.DataFrame(records, dtype=str)


def set_emails(records):
    email.EMAILS = pd.DataFrame(records, dtype=str)


def set_directory(addresses):
    company_directory.EMAILS = pd.DataFrame({"email_address": addresses})


def seed_data(test_name):
    """Reset domain state and seed all input data for the given test.

    Every test's input data lives here, outside the test functions, so each
    test body contains only the user query, the tool-call chain, and asserts.
    """
    if test_name == "test_create_confirm_reschedule_cancel_event":
        calendar.reset_state()
        set_events(
            [
                {
                    "event_id": "00000001",
                    "event_name": "Standup",
                    "participant_email": "team@mail.com",
                    "event_start": "2025-01-01 09:00:00",
                    "duration": "15",
                }
            ]
        )
    elif test_name == "test_search_meeting_with_sam_then_get_start_time":
        calendar.reset_state()
        set_events(
            [
                {
                    "event_id": "00000010",
                    "event_name": "Sync with Rio",
                    "participant_email": "rio@mail.com",
                    "event_start": "2025-01-05 09:00:00",
                    "duration": "30",
                },
                {
                    "event_id": "00000011",
                    "event_name": "Lunch",
                    "participant_email": "rio@mail.com",
                    "event_start": "2025-01-05 12:00:00",
                    "duration": "60",
                },
            ]
        )
    elif test_name == "test_lookup_fatima_book_then_cancel_immediately":
        calendar.reset_state()
        set_directory(["simone.blaine@mail.com", "marlo.reed@mail.com"])
        set_events(
            [
                {
                    "event_id": "00000005",
                    "event_name": "Kickoff",
                    "participant_email": "team@mail.com",
                    "event_start": "2025-01-01 09:00:00",
                    "duration": "30",
                }
            ]
        )
    elif test_name == "test_search_sam_meeting_and_reschedule":
        calendar.reset_state()
        set_events(
            [
                {
                    "event_id": "00000020",
                    "event_name": "Sync with Rio",
                    "participant_email": "rio@mail.com",
                    "event_start": "2025-01-02 08:00:00",
                    "duration": "30",
                }
            ]
        )
    elif test_name == "test_reply_to_budget_email_and_forward_to_yuki":
        email.reset_state()
        set_emails(
            [
                {
                    "email_id": "1",
                    "inbox/outbox": "inbox",
                    "sender/recipient": "elara.pryor@mail.com",
                    "subject": "Q3 Budget Review",
                    "sent_datetime": "2025-01-10 09:00:00",
                    "body": "Please review the attached budget.",
                },
                {
                    "email_id": "2",
                    "inbox/outbox": "inbox",
                    "sender/recipient": "rio@mail.com",
                    "subject": "Lunch",
                    "sent_datetime": "2025-01-11 09:00:00",
                    "body": "Lunch?",
                },
            ]
        )
        set_directory(["sennen.marsh@mail.com"])
    elif test_name == "test_lookup_dmitri_send_reminder_then_verify":
        email.reset_state()
        set_directory(["rourke.frost@mail.com"])
        set_emails(
            [
                {
                    "email_id": "5",
                    "inbox/outbox": "inbox",
                    "sender/recipient": "someone@mail.com",
                    "subject": "Old",
                    "sent_datetime": "2025-01-01 09:00:00",
                    "body": "old body",
                }
            ]
        )
    elif test_name == "test_send_test_email_then_find_and_delete_it":
        email.reset_state()
        set_emails(
            [
                {
                    "email_id": "9",
                    "inbox/outbox": "inbox",
                    "sender/recipient": "a@mail.com",
                    "subject": "Other",
                    "sent_datetime": "2025-01-01 09:00:00",
                    "body": "x",
                }
            ]
        )
    elif test_name == "test_reply_to_vacation_request_email":
        email.reset_state()
        set_emails(
            [
                {
                    "email_id": "20",
                    "inbox/outbox": "inbox",
                    "sender/recipient": "lira.vale@mail.com",
                    "subject": "Vacation Request",
                    "sent_datetime": "2025-01-01 09:00:00",
                    "body": "Requesting time off next week.",
                }
            ]
        )
    elif test_name == "test_check_security_email_subject_then_forward_to_grace":
        email.reset_state()
        set_emails(
            [
                {
                    "email_id": "30",
                    "inbox/outbox": "inbox",
                    "sender/recipient": "security@mail.com",
                    "subject": "Security Incident Report",
                    "sent_datetime": "2025-01-01 09:00:00",
                    "body": "We detected unusual login activity.",
                }
            ]
        )
        set_directory(["wren.mercer@mail.com"])
    elif test_name == "test_delete_promotional_newsletter_email":
        email.reset_state()
        set_emails(
            [
                {
                    "email_id": "40",
                    "inbox/outbox": "inbox",
                    "sender/recipient": "promo@mail.com",
                    "subject": "Newsletter Promo",
                    "sent_datetime": "2025-01-01 09:00:00",
                    "body": "Check our latest deals.",
                }
            ]
        )
    elif test_name == "test_lookup_kofi_create_task_then_confirm_due_date":
        project_management.reset_state()
        set_tasks(
            [
                {
                    "task_id": "00000001",
                    "task_name": "Existing Task",
                    "assigned_to_email": "zayd.dane@mail.com",
                    "list_name": "Backlog",
                    "due_date": "2025-01-01",
                    "board": "Back end",
                }
            ]
        )
        set_directory(["zayd.dane@mail.com"])
    elif test_name == "test_search_launch_plan_task_and_move_to_in_review":
        project_management.reset_state()
        set_tasks(
            [
                {
                    "task_id": "00000010",
                    "task_name": "Prepare Q3 product launch plan",
                    "assigned_to_email": "talia.holt@mail.com",
                    "list_name": "In Progress",
                    "due_date": "2025-01-01",
                    "board": "Design",
                }
            ]
        )
    elif test_name == "test_search_carlos_completed_task_and_delete_duplicate":
        project_management.reset_state()
        set_tasks(
            [
                {
                    "task_id": "00000015",
                    "task_name": "Review marketing brief",
                    "assigned_to_email": "marlo.reed@mail.com",
                    "list_name": "Completed",
                    "due_date": "2025-01-01",
                    "board": "Design",
                }
            ]
        )
        set_directory(["marlo.reed@mail.com"])
    elif test_name == "test_reassign_yukis_login_bug_task_to_carlos":
        project_management.reset_state()
        set_tasks(
            [
                {
                    "task_id": "00000020",
                    "task_name": "Fix login bug",
                    "assigned_to_email": "sennen.marsh@mail.com",
                    "list_name": "In Progress",
                    "due_date": "2025-01-01",
                    "board": "Back end",
                },
                {
                    "task_id": "00000021",
                    "task_name": "Other work",
                    "assigned_to_email": "marlo.reed@mail.com",
                    "list_name": "Backlog",
                    "due_date": "2025-01-01",
                    "board": "Design",
                },
            ]
        )
        set_directory(["sennen.marsh@mail.com", "marlo.reed@mail.com"])
    elif test_name == "test_search_release_notes_task_then_get_due_date_and_delete":
        project_management.reset_state()
        set_tasks(
            [
                {
                    "task_id": "00000030",
                    "task_name": "Draft release notes",
                    "assigned_to_email": "sennen.marsh@mail.com",
                    "list_name": "Completed",
                    "due_date": "2025-01-01",
                    "board": "Design",
                }
            ]
        )
    elif test_name == "test_lookup_priya_create_task_then_confirm_assignee":
        project_management.reset_state()
        set_tasks(
            [
                {
                    "task_id": "00000040",
                    "task_name": "Existing",
                    "assigned_to_email": "odile.stone@mail.com",
                    "list_name": "Backlog",
                    "due_date": "2025-01-01",
                    "board": "Design",
                }
            ]
        )
        set_directory(["odile.stone@mail.com"])
    elif test_name == "test_search_morgan_patel_and_update_status_to_won":
        crm.reset_state()
        set_customers(
            [
                {
                    "customer_id": "00000001",
                    "customer_name": "Blaise Corwin",
                    "customer_email": "blaise.corwin@mail.com",
                    "customer_phone": "555-0101",
                    "last_contact_date": "2025-01-01",
                    "product_interest": "Consulting",
                    "status": "Proposal",
                    "assigned_to_email": "emily.davis@mail.com",
                    "notes": "",
                    "follow_up_by": "2025-02-01",
                }
            ]
        )
    elif test_name == "test_lookup_priya_add_temp_customer_then_remove_immediately":
        crm.reset_state()
        set_customers(
            [
                {
                    "customer_id": "00000001",
                    "customer_name": "Baseline Co",
                    "customer_email": "baseline@mail.com",
                    "customer_phone": "555-0100",
                    "last_contact_date": "2025-01-01",
                    "product_interest": "Software",
                    "status": "Lead",
                    "assigned_to_email": "emily.davis@mail.com",
                    "notes": "",
                    "follow_up_by": "2025-02-01",
                }
            ]
        )
        set_directory(["odile.stone@mail.com"])
    elif test_name == "test_search_alex_jackson_and_reassign_to_raj":
        crm.reset_state()
        set_customers(
            [
                {
                    "customer_id": "00000005",
                    "customer_name": "Tamsin Vye",
                    "customer_email": "tamsin.vye@mail.com",
                    "customer_phone": "555-0102",
                    "last_contact_date": "2025-01-01",
                    "product_interest": "Consulting",
                    "status": "Qualified",
                    "assigned_to_email": "sophia.lee@mail.com",
                    "notes": "",
                    "follow_up_by": "2025-02-01",
                }
            ]
        )
        set_directory(["dorian.calder@mail.com"])
    elif test_name == "test_lookup_sofia_add_quinn_robinson_then_confirm_record":
        crm.reset_state()
        set_customers(
            [
                {
                    "customer_id": "00000001",
                    "customer_name": "Baseline Co",
                    "customer_email": "baseline@mail.com",
                    "customer_phone": "555-0100",
                    "last_contact_date": "2025-01-01",
                    "product_interest": "Software",
                    "status": "Lead",
                    "assigned_to_email": "emily.davis@mail.com",
                    "notes": "",
                    "follow_up_by": "2025-02-01",
                }
            ]
        )
        set_directory(["neve.quinn@mail.com"])
    elif test_name == "test_search_kerry_robinson_and_delete_customer":
        crm.reset_state()
        set_customers(
            [
                {
                    "customer_id": "00000009",
                    "customer_name": "Rhea Calloway",
                    "customer_email": "rhea.calloway@mail.com",
                    "customer_phone": "555-0199",
                    "last_contact_date": "2025-01-01",
                    "product_interest": "Consulting",
                    "status": "Proposal",
                    "assigned_to_email": "harlow.dunn@mail.com",
                    "notes": "",
                    "follow_up_by": "2025-02-01",
                }
            ]
        )
    elif test_name == "test_total_visits_then_plot_busiest_day":
        analytics.reset_state()
        set_analytics_data(
            [
                {"date_of_visit": "2024-02-01", "visitor_id": "1", "page_views": "1", "session_duration_seconds": "5.0", "traffic_source": "direct", "user_engaged": "False"},
                {"date_of_visit": "2024-02-02", "visitor_id": "2", "page_views": "2", "session_duration_seconds": "6.0", "traffic_source": "direct", "user_engaged": "True"},
                {"date_of_visit": "2024-02-02", "visitor_id": "3", "page_views": "1", "session_duration_seconds": "7.0", "traffic_source": "search engine", "user_engaged": "True"},
                {"date_of_visit": "2024-02-02", "visitor_id": "4", "page_views": "3", "session_duration_seconds": "8.0", "traffic_source": "referral", "user_engaged": "False"},
                {"date_of_visit": "2024-02-03", "visitor_id": "5", "page_views": "1", "session_duration_seconds": "4.0", "traffic_source": "direct", "user_engaged": "False"},
            ]
        )
    elif test_name == "test_average_session_duration_then_plot_highest_day":
        analytics.reset_state()
        set_analytics_data(
            [
                {"date_of_visit": "2024-02-01", "visitor_id": "1", "page_views": "1", "session_duration_seconds": "5.0", "traffic_source": "direct", "user_engaged": "False"},
                {"date_of_visit": "2024-02-02", "visitor_id": "2", "page_views": "2", "session_duration_seconds": "6.0", "traffic_source": "direct", "user_engaged": "True"},
                {"date_of_visit": "2024-02-02", "visitor_id": "3", "page_views": "1", "session_duration_seconds": "9.0", "traffic_source": "search engine", "user_engaged": "True"},
                {"date_of_visit": "2024-02-03", "visitor_id": "4", "page_views": "1", "session_duration_seconds": "4.0", "traffic_source": "direct", "user_engaged": "False"},
            ]
        )
    elif test_name == "test_get_visitor_info_then_total_visits_for_that_day":
        analytics.reset_state()
        set_analytics_data(
            [
                {"date_of_visit": "2024-03-01", "visitor_id": "100", "page_views": "1", "session_duration_seconds": "5.0", "traffic_source": "direct", "user_engaged": "False"},
                {"date_of_visit": "2024-03-01", "visitor_id": "101", "page_views": "2", "session_duration_seconds": "6.0", "traffic_source": "referral", "user_engaged": "True"},
                {"date_of_visit": "2024-03-02", "visitor_id": "102", "page_views": "1", "session_duration_seconds": "3.0", "traffic_source": "direct", "user_engaged": "False"},
            ]
        )
    elif test_name == "test_engaged_users_then_traffic_source_for_top_day":
        analytics.reset_state()
        set_analytics_data(
            [
                {"date_of_visit": "2024-04-01", "visitor_id": "200", "page_views": "1", "session_duration_seconds": "5.0", "traffic_source": "direct", "user_engaged": "True"},
                {"date_of_visit": "2024-04-01", "visitor_id": "201", "page_views": "2", "session_duration_seconds": "6.0", "traffic_source": "search engine", "user_engaged": "True"},
                {"date_of_visit": "2024-04-02", "visitor_id": "202", "page_views": "1", "session_duration_seconds": "3.0", "traffic_source": "direct", "user_engaged": "False"},
            ]
        )
    elif test_name == "test_traffic_source_then_plot_top_search_engine_day":
        analytics.reset_state()
        set_analytics_data(
            [
                {"date_of_visit": "2024-05-01", "visitor_id": "300", "page_views": "1", "session_duration_seconds": "5.0", "traffic_source": "search engine", "user_engaged": "True"},
                {"date_of_visit": "2024-05-02", "visitor_id": "301", "page_views": "1", "session_duration_seconds": "5.0", "traffic_source": "search engine", "user_engaged": "True"},
                {"date_of_visit": "2024-05-02", "visitor_id": "302", "page_views": "1", "session_duration_seconds": "5.0", "traffic_source": "search engine", "user_engaged": "True"},
                {"date_of_visit": "2024-05-03", "visitor_id": "303", "page_views": "1", "session_duration_seconds": "5.0", "traffic_source": "direct", "user_engaged": "False"},
            ]
        )
    elif test_name == "test_get_visitor_info_then_average_session_duration_for_that_day":
        analytics.reset_state()
        set_analytics_data(
            [
                {"date_of_visit": "2024-06-01", "visitor_id": "400", "page_views": "1", "session_duration_seconds": "10.0", "traffic_source": "direct", "user_engaged": "False"},
                {"date_of_visit": "2024-06-01", "visitor_id": "401", "page_views": "2", "session_duration_seconds": "20.0", "traffic_source": "referral", "user_engaged": "True"},
            ]
        )
    elif test_name == "test_engaged_users_then_plot_top_engagement_day":
        analytics.reset_state()
        set_analytics_data(
            [
                {"date_of_visit": "2024-07-01", "visitor_id": "500", "page_views": "1", "session_duration_seconds": "5.0", "traffic_source": "direct", "user_engaged": "True"},
                {"date_of_visit": "2024-07-02", "visitor_id": "501", "page_views": "1", "session_duration_seconds": "5.0", "traffic_source": "direct", "user_engaged": "True"},
                {"date_of_visit": "2024-07-02", "visitor_id": "502", "page_views": "1", "session_duration_seconds": "5.0", "traffic_source": "direct", "user_engaged": "True"},
            ]
        )


def test_create_confirm_reschedule_cancel_event():
    # User query: "Schedule a 45-minute sync with the design team at
    # 2025-03-04 09:00:00, confirm its duration, then reschedule it to
    # 10:00, and cancel it since the room got double-booked."
    # Chain: create_event -> get_event_information_by_id -> update_event -> delete_event

    new_id = create_event("Design Sync", "design-team@mail.com", "2025-03-04 09:00:00", "45")
    info = get_event_information_by_id(new_id, "duration")
    upd = update_event(new_id, "event_start", "2025-03-04 10:00:00")
    assert upd == "Event updated successfully."
    new_start = calendar.CALENDAR_EVENTS.loc[
        calendar.CALENDAR_EVENTS["event_id"] == new_id, "event_start"
    ].values[0]
    assert new_start == "2025-03-04 10:00:00"

    deleted = delete_event(new_id)
    assert deleted == "Event deleted successfully."

    # Incorrect — do not imitate: calling delete_event without an id.
    assert delete_event() == "Event ID not provided."


def test_search_meeting_with_sam_then_get_start_time():
    # User query: "Find my meeting with Rio that's a sync, and tell me
    # exactly when it starts."
    # Chain: search_events -> get_event_information_by_id

    results = search_events("Sync with Rio")
    assert len(results) == 1
    eid = results[0]["event_id"]

    info = get_event_information_by_id(eid, "event_start")
    assert info == {"event_start": "2025-01-05 09:00:00"}


def test_lookup_fatima_book_then_cancel_immediately():
    # User query: "Book a 20-minute call with Simone at
    # 2025-04-01 11:00:00 — actually cancel it, I need to check her
    # availability first."
    # Immediate execution example: all data is available up front, so the
    # lookup, booking, and cancellation happen without asking questions.
    # Chain: find_email_address -> create_event -> delete_event

    emails = find_email_address("Simone")
    assert len(emails) == 1

    new_id = create_event("Call with Simone", str(emails[0]), "2025-04-01 11:00:00", "20")
    deleted = delete_event(new_id)
    assert deleted == "Event deleted successfully."


def test_search_sam_meeting_and_reschedule():
    # User query: "Find the meeting with Rio and push it back one hour
    # to 2025-01-02 09:00:00."
    # Chain: search_events -> update_event

    results = search_events("Rio")
    assert len(results) == 1
    eid = results[0]["event_id"]

    upd = update_event(eid, "event_start", "2025-01-02 09:00:00")
    assert upd == "Event updated successfully."
    new_start = calendar.CALENDAR_EVENTS.loc[
        calendar.CALENDAR_EVENTS["event_id"] == eid, "event_start"
    ].values[0]
    assert new_start == "2025-01-02 09:00:00"

    # Incorrect — do not imitate: update_event with a missing new_value.
    assert update_event(eid, "event_start") == "Event ID, field, or new value not provided."



def test_reply_to_budget_email_and_forward_to_yuki():
    # User query: "Reply to the latest email about the budget thanking
    # them, and forward that same email to Sennen."
    # Chain: search_emails -> reply_email, find_email_address -> forward_email

    results = search_emails("budget")
    assert len(results) == 1
    eid = results[0]["email_id"]

    reply = reply_email(eid, "Thanks for sending the budget review.")
    assert reply == "Email replied successfully."

    sennen = find_email_address("Sennen")
    assert len(sennen) == 1
    fwd = forward_email(eid, str(sennen[0]))
    assert fwd == "Email forwarded successfully."

    # Incorrect — do not imitate: forwarding using a name instead of the
    # full email address returned by find_email_address.
    assert forward_email(eid, "sennen") == "Invalid recipient email address."


def test_lookup_dmitri_send_reminder_then_verify():
    # User query: "Send Rourke a reminder about tomorrow's 9am meeting,
    # then confirm the email went to the correct address."
    # Immediate execution example: the recipient name and message content
    # are already known, so the lookup + send happen without questions.
    # Chain: find_email_address -> send_email -> search_emails -> get_email_information_by_id

    emails = find_email_address("Rourke")
    assert len(emails) == 1

    sent = send_email(str(emails[0]), "Meeting Reminder", "Don't forget tomorrow's 9am meeting.")
    assert sent == "Email sent successfully."

    search = search_emails("Meeting Reminder")
    assert len(search) == 1
    new_id = search[0]["email_id"]

    info = get_email_information_by_id(new_id, "sender/recipient")
    assert info == {"sender/recipient": emails[0]}

    # Incorrect — do not imitate: passing a bare name instead of a full
    # email address to send_email.
    assert send_email("rourke", "x", "y") == "Invalid recipient email address."


def test_send_test_email_then_find_and_delete_it():
    # User query: "I accidentally sent Zayd a test email with subject
    # 'Test Ignore' — find it and delete it."
    # Chain: send_email -> search_emails -> delete_email
    sent = send_email("zayd.dane@mail.com", "Test Ignore", "please ignore")
    assert sent == "Email sent successfully."

    # The sent email is retrieved by subject, then its id feeds delete_email.
    search = search_emails("Test Ignore")
    assert len(search) == 1
    new_id = search[0]["email_id"]
    assert new_id == "10"

    deleted = delete_email(new_id)
    assert deleted == "Email deleted successfully."

    # Incorrect — do not imitate: calling delete_email without an id.
    assert delete_email() == "Email ID not provided."


def test_reply_to_vacation_request_email():
    # User query: "Reply to the email about the vacation request
    # approving it."
    # Chain: search_emails -> reply_email

    results = search_emails("vacation request")
    assert len(results) == 1
    eid = results[0]["email_id"]

    reply = reply_email(eid, "Approved, enjoy your time off.")
    assert reply == "Email replied successfully."

    # Incorrect — do not imitate: reply_email with a missing body.
    assert reply_email(eid) == "Email ID or body not provided."


def test_check_security_email_subject_then_forward_to_grace():
    # User query: "Check the subject of the security incident email and
    # forward it to Wren."
    # Chain: search_emails -> get_email_information_by_id, find_email_address -> forward_email

    results = search_emails("security incident")
    assert len(results) == 1
    eid = results[0]["email_id"]

    subj = get_email_information_by_id(eid, "subject")
    assert subj == {"subject": "Security Incident Report"}

    wren = find_email_address("Wren")
    assert len(wren) == 1
    fwd = forward_email(eid, str(wren[0]))
    assert fwd == "Email forwarded successfully."


def test_delete_promotional_newsletter_email():
    # User query: "Delete the promotional newsletter email."
    # Chain: search_emails -> delete_email

    results = search_emails("newsletter promo")
    assert len(results) == 1
    eid = results[0]["email_id"]

    deleted = delete_email(eid)
    assert deleted == "Email deleted successfully."

    # Incorrect — do not imitate: deleting an id that doesn't exist.
    assert delete_email("999") == "Email not found."



def test_lookup_kofi_create_task_then_confirm_due_date():
    # User query: "Create a new task 'Update security patches' for Zayd
    # in the Backlog on the Back end board due 2025-02-01, then confirm
    # its due date."
    # Immediate execution example: assignee, list, board, and due date
    # are all known, so the lookup + creation happen without questions.
    # Chain: find_email_address -> create_task -> get_task_information_by_id

    emails = find_email_address("Zayd")
    assert len(emails) == 1

    new_id = create_task(
        "Update security patches", str(emails[0]), "Backlog", "2025-02-01", "Back end"
    )
    assert new_id == "00000002"

    info = get_task_information_by_id(new_id, "due_date")
    assert info == {"due_date": "2025-02-01"}

    # Incorrect — do not imitate: create_task with a missing board.
    bad = create_task("X", str(emails[0]), "Backlog", "2025-02-01")
    assert bad == "Missing task details."


def test_search_launch_plan_task_and_move_to_in_review():
    # User query: "Move the 'Prepare Q3 product launch plan' task to
    # In Review."
    # Chain: search_tasks -> update_task

    results = search_tasks(task_name="Prepare Q3 product launch plan")
    assert len(results) == 1
    tid = results[0]["task_id"]

    upd = update_task(tid, "list_name", "In Review")
    assert upd == "Task updated successfully."

    # Incorrect — do not imitate: update_task with an invalid list name.
    assert update_task(tid, "list_name", "Not A Real List") == "List not valid. Please choose from: 'Backlog', 'In Progress', 'In Review', 'Completed'."


def test_search_carlos_completed_task_and_delete_duplicate():
    # User query: "Delete Marlo's completed task about the marketing
    # brief since it's a duplicate."
    # Chain: find_email_address -> search_tasks -> delete_task

    # Resolve the name "Marlo" to a full email before searching tasks.
    emails = find_email_address("Marlo")
    assert len(emails) == 1

    results = search_tasks(assigned_to_email=str(emails[0]), list_name="Completed")
    assert len(results) == 1
    tid = results[0]["task_id"]

    deleted = delete_task(tid)
    assert deleted == "Task deleted successfully."

    # Incorrect — do not imitate: calling delete_task without an id.
    assert delete_task() == "Task ID not provided."


def test_reassign_yukis_login_bug_task_to_carlos():
    # User query: "Reassign Sennen's 'Fix login bug' task to Marlo."
    # Chain: find_email_address (x2) -> search_tasks -> update_task

    sennen_emails = find_email_address("Sennen")
    assert len(sennen_emails) == 1
    marlo_emails = find_email_address("Marlo")
    assert len(marlo_emails) == 1

    results = search_tasks(assigned_to_email=str(sennen_emails[0]), task_name="Fix login bug")
    assert len(results) == 1
    tid = results[0]["task_id"]

    upd = update_task(tid, "assigned_to_email", str(marlo_emails[0]))
    assert upd == "Task updated successfully."
    new_assignee = project_management.PROJECT_TASKS.loc[
        project_management.PROJECT_TASKS["task_id"] == tid, "assigned_to_email"
    ].values[0]
    assert new_assignee == marlo_emails[0]


def test_search_release_notes_task_then_get_due_date_and_delete():
    # User query: "Look up the due date of the task 'Draft release
    # notes', and delete it since it's already completed."
    # Chain: search_tasks -> get_task_information_by_id -> delete_task

    results = search_tasks(task_name="Draft release notes")
    assert len(results) == 1
    tid = results[0]["task_id"]

    info = get_task_information_by_id(tid, "due_date")
    assert info == {"due_date": "2025-01-01"}

    deleted = delete_task(tid)
    assert deleted == "Task deleted successfully."


def test_lookup_priya_create_task_then_confirm_assignee():
    # User query: "Create a task 'Draft Q3 budget review' for Odile due
    # 2025-05-01 on the Design board in Backlog, then confirm who it's
    # assigned to."
    # Chain: find_email_address -> create_task -> get_task_information_by_id

    emails = find_email_address("Odile")
    assert len(emails) == 1

    new_id = create_task(
        "Draft Q3 budget review", str(emails[0]), "Backlog", "2025-05-01", "Design"
    )
    assert new_id == "00000041"

    info = get_task_information_by_id(new_id, "assigned_to_email")
    assert info == {"assigned_to_email": emails[0]}

    # Incorrect — do not imitate: create_task with an invalid board name.
    bad = create_task("X", str(emails[0]), "Backlog", "2025-05-01", "Marketing")
    assert bad == "Board not valid. Please choose from: 'Back end', 'Front end', 'Design'."



def test_search_morgan_patel_and_update_status_to_won():
    # User query: "Update Blaise Corwin's CRM status to Won."
    # Chain: search_customers -> update_customer

    results = search_customers(customer_name="Blaise Corwin")
    assert len(results) == 1
    cid = results[0]["customer_id"]

    upd = update_customer(cid, "status", "Won")
    assert upd == "Customer updated successfully."

    # Incorrect — do not imitate: update_customer with an invalid status.
    assert update_customer(cid, "status", "Closed") == "Status not valid. Please choose from: 'Qualified', 'Won', 'Lost', 'Lead', 'Proposal'"


def test_lookup_priya_add_temp_customer_then_remove_immediately():
    # User query: "Add 'Temp Test Co' as a Lead assigned to Odile, then
    # remove them right away since it was a testing entry."
    # Immediate execution example: the name, status, and assignee are
    # all known, so the add + removal happen without questions.
    # Chain: find_email_address -> add_customer -> delete_customer

    emails = find_email_address("Odile")
    assert len(emails) == 1

    new_id = add_customer("Temp Test Co", str(emails[0]), "Lead")
    assert isinstance(new_id, str)
    assert new_id != ""

    deleted = delete_customer(new_id)
    assert deleted == "Customer deleted successfully."

    # Incorrect — do not imitate: deleting a customer_id that was already removed.
    assert delete_customer(new_id) == "Customer not found."


def test_search_alex_jackson_and_reassign_to_raj():
    # User query: "Dorian is taking over Tamsin Vye's account — reassign
    # it to him in the CRM."
    # Chain: search_customers -> find_email_address -> update_customer

    results = search_customers(customer_name="Tamsin Vye")
    assert len(results) == 1
    cid = results[0]["customer_id"]

    dorian_emails = find_email_address("Dorian")
    assert len(dorian_emails) == 1

    upd = update_customer(cid, "assigned_to_email", str(dorian_emails[0]))
    assert upd == "Customer updated successfully."
    new_owner = crm.CRM_DATA.loc[crm.CRM_DATA["customer_id"] == cid, "assigned_to_email"].values[0]
    assert new_owner == dorian_emails[0]


def test_lookup_sofia_add_quinn_robinson_then_confirm_record():
    # User query: "Add Marlowe Quist as a new Proposal lead assigned to
    # Neve, interested in Hardware, then confirm the record was
    # created correctly."
    # Chain: find_email_address -> add_customer -> search_customers

    emails = find_email_address("Neve")
    assert len(emails) == 1

    new_id = add_customer(
        "Marlowe Quist", str(emails[0]), "Proposal", product_interest="Hardware"
    )
    assert isinstance(new_id, str)

    results = search_customers(customer_name="Marlowe Quist")
    assert len(results) == 1
    assert results[0]["customer_id"] == new_id
    assert results[0]["product_interest"] == "Hardware"
    assert results[0]["assigned_to_email"] == emails[0]


def test_search_kerry_robinson_and_delete_customer():
    # User query: "Rhea Calloway is no longer a customer — delete
    # their CRM record."
    # Chain: search_customers -> delete_customer

    results = search_customers(customer_name="Rhea Calloway")
    assert len(results) == 1
    cid = results[0]["customer_id"]

    deleted = delete_customer(cid)
    assert deleted == "Customer deleted successfully."

    # Incorrect — do not imitate: calling delete_customer without an id.
    assert delete_customer() == "Customer ID not provided."



def test_total_visits_then_plot_busiest_day():
    # User query: "Create a bar chart of total visits for the busiest
    # day between 2024-02-01 and 2024-02-03."
    # Chain: total_visits_count -> create_plot

    visits = total_visits_count("2024-02-01", "2024-02-03")
    busiest = max(visits, key=visits.get)
    plot = create_plot(busiest, busiest, "total_visits", "bar")
    # Incorrect — do not imitate: create_plot with an invalid metric name.
    bad = create_plot("2024-02-01", "2024-02-03", "not_a_metric", "bar")
    assert isinstance(bad, str)
    assert "plots/" not in bad


def test_average_session_duration_then_plot_highest_day():
    # User query: "Make a line chart of the day with the highest
    # average session duration between 2024-02-01 and 2024-02-03."
    # Chain: get_average_session_duration -> create_plot

    durations = get_average_session_duration("2024-02-01", "2024-02-03")
    highest = max(durations, key=durations.get)
    plot = create_plot(highest, highest, "session_duration_seconds", "line")
    assert plot == "plots/2024-02-02_2024-02-02_session_duration_seconds_line.png"


def test_get_visitor_info_then_total_visits_for_that_day():
    # User query: "Look up visitor 100's info, then tell me how many
    # total visits happened on that same day."
    # Chain: get_visitor_information_by_id -> total_visits_count

    visitor = get_visitor_information_by_id("100")
    date = visitor[0]["date_of_visit"]
    counts = total_visits_count(date, date)
    assert counts == {"2024-03-01": 2}

    # Incorrect — do not imitate: calling get_visitor_information_by_id without an id.
    assert get_visitor_information_by_id() == "Visitor ID not provided."


def test_engaged_users_then_traffic_source_for_top_day():
    # User query: "How many engaged users were there between 2024-04-01
    # and 2024-04-02, and what search-engine traffic did the
    # most-engaged day have?"
    # Chain: engaged_users_count -> traffic_source_count

    engaged = engaged_users_count("2024-04-01", "2024-04-02")
    best_day = max(engaged, key=engaged.get)
    traffic = traffic_source_count(best_day, best_day, "search engine")
    assert traffic == {"2024-04-01": 1}


def test_traffic_source_then_plot_top_search_engine_day():
    # User query: "Create a scatter plot of total visits for the day
    # with the most search-engine traffic between 2024-05-01 and
    # 2024-05-03."
    # Chain: traffic_source_count -> create_plot

    counts = traffic_source_count("2024-05-01", "2024-05-03", "search engine")
    best = max(counts, key=counts.get)
    plot = create_plot(best, best, "total_visits", "scatter")
    assert plot == "plots/2024-05-02_2024-05-02_total_visits_scatter.png"


def test_get_visitor_info_then_average_session_duration_for_that_day():
    # User query: "Look up visitor 400's visit date, then tell me the
    # average session duration for that day."
    # Chain: get_visitor_information_by_id -> get_average_session_duration

    visitor = get_visitor_information_by_id("400")
    date = visitor[0]["date_of_visit"]
    avg = get_average_session_duration(date, date)
    assert avg == {"2024-06-01": 15.0}


def test_engaged_users_then_plot_top_engagement_day():
    # User query: "Create a bar chart of engaged users for the day with
    # the highest engagement between 2024-07-01 and 2024-07-02."
    # Chain: engaged_users_count -> create_plot

    engaged = engaged_users_count("2024-07-01", "2024-07-02")
    best = max(engaged, key=engaged.get)
    plot = create_plot(best, best, "user_engaged", "bar")
    assert plot == "plots/2024-07-02_2024-07-02_user_engaged_bar.png"



def _run_all_tests():
    current_module = sys.modules[__name__]
    test_functions = [
        (name, obj)
        for name, obj in vars(current_module).items()
        if name.startswith("test_") and callable(obj)
    ]
    test_functions.sort(key=lambda item: item[1].__code__.co_firstlineno)

    failures = []
    for name, func in test_functions:
        seed_data(name)
        try:
            func()
        except Exception as exc:  # noqa: BLE001 - report every failure, then continue
            failures.append((name, exc))
            print(f"FAILED: {name}: {exc}")
        else:
            print(f"PASSED: {name}")

    print(f"\nRan {len(test_functions)} tests, {len(failures)} failed.")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    _run_all_tests()
