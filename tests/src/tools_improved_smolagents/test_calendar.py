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

smolagents_stub = types.ModuleType("smolagents")
smolagents_stub.tool = lambda func: func
sys.modules["smolagents"] = smolagents_stub

import pandas as pd
import pytest

calendar = importlib.import_module("src.tools_improved_smolagents.calendar")


TEST_EVENTS = [
    {
        "event_id": "70838584",
        "event_name": "Board of Directors Meeting",
        "participant_email": "Yuki.Tanaka@company.com",
        "event_start": "2023-10-01 10:00:00",
        "duration": "60",
    },
    {
        "event_id": "70838585",
        "event_name": "Meeting with Sam",
        "participant_email": "sam@company.com",
        "event_start": "2023-10-02 11:00:00",
        "duration": "60",
    },
    {
        "event_id": "70838586",
        "event_name": "Product Review",
        "participant_email": "alex@company.com",
        "event_start": "2023-10-03 15:00:00",
        "duration": "30",
    },
]


@pytest.fixture(autouse=True)
def calendar_events():
    calendar.CALENDAR_EVENTS = pd.DataFrame(TEST_EVENTS)
    yield
    calendar.CALENDAR_EVENTS = pd.DataFrame(TEST_EVENTS)


def call_tool(tool_obj, *args, **kwargs):
    if hasattr(tool_obj, "func"):
        return tool_obj.func(*args, **kwargs)
    if hasattr(tool_obj, "forward"):
        return tool_obj.forward(*args, **kwargs)
    return tool_obj(*args, **kwargs)


def test_get_event_information_by_id_returns_requested_field():
    assert call_tool(calendar.get_event_information_by_id, "70838584", "event_name") == {
        "event_name": "Board of Directors Meeting"
    }


def test_get_event_information_by_id_handles_missing_and_unknown_fields():
    assert call_tool(calendar.get_event_information_by_id) == "Event ID not provided."
    assert call_tool(calendar.get_event_information_by_id, "70838584") == "Field not provided."
    assert call_tool(calendar.get_event_information_by_id, "70838584", "unknown") == "Field not found."
    assert call_tool(calendar.get_event_information_by_id, "00000000", "event_name") == "Event not found."


def test_search_events_matches_name_or_email_case_insensitively():
    assert call_tool(calendar.search_events, "yuki") == [
        {
            "event_id": "70838584",
            "event_name": "Board of Directors Meeting",
            "participant_email": "Yuki.Tanaka@company.com",
            "event_start": "2023-10-01 10:00:00",
            "duration": "60",
        }
    ]
    assert call_tool(calendar.search_events, "product")[0]["event_id"] == "70838586"


def test_search_events_filters_by_time_range():
    assert call_tool(
        calendar.search_events,
        time_min="2023-10-02 00:00:00",
        time_max="2023-10-02 23:59:59",
    ) == [
        {
            "event_id": "70838585",
            "event_name": "Meeting with Sam",
            "participant_email": "sam@company.com",
            "event_start": "2023-10-02 11:00:00",
            "duration": "60",
        }
    ]


def test_search_events_returns_message_when_no_events_match():
    assert call_tool(calendar.search_events, "does-not-exist") == "No events found."


def test_search_events_limits_results_to_five():
    calendar.CALENDAR_EVENTS = pd.DataFrame(
        [
            {
                "event_id": str(i).zfill(8),
                "event_name": f"Planning Meeting {i}",
                "participant_email": f"person{i}@company.com",
                "event_start": f"2023-10-{i + 1:02d} 10:00:00",
                "duration": "30",
            }
            for i in range(7)
        ]
    )

    results = call_tool(calendar.search_events, "meeting")

    assert len(results) == 5
    assert [event["event_id"] for event in results] == ["00000000", "00000001", "00000002", "00000003", "00000004"]


def test_create_event_appends_event_and_normalizes_email():
    new_id = call_tool(
        calendar.create_event,
        "Design Review",
        "Designer@Company.com",
        "2023-10-04 09:00:00",
        "45",
    )

    new_event = calendar.CALENDAR_EVENTS[calendar.CALENDAR_EVENTS["event_id"] == new_id].iloc[0]
    assert new_id == "70838587"
    assert new_event["event_name"] == "Design Review"
    assert new_event["participant_email"] == "designer@company.com"


def test_create_event_validates_required_arguments():
    assert call_tool(calendar.create_event) == "Event name not provided."
    assert call_tool(calendar.create_event, "Meeting") == "Participant email not provided."
    assert call_tool(calendar.create_event, "Meeting", "sam@company.com") == "Event start not provided."
    assert (
        call_tool(calendar.create_event, "Meeting", "sam@company.com", "2023-10-04 09:00:00")
        == "Event duration not provided."
    )


def test_delete_event_removes_existing_event():
    assert call_tool(calendar.delete_event, "70838585") == "Event deleted successfully."
    assert "70838585" not in calendar.CALENDAR_EVENTS["event_id"].values


def test_delete_event_handles_missing_or_unknown_id():
    assert call_tool(calendar.delete_event) == "Event ID not provided."
    assert call_tool(calendar.delete_event, "00000000") == "Event not found."


def test_update_event_changes_field_and_normalizes_email():
    assert call_tool(calendar.update_event, "70838584", "event_name", "New Event Name") == "Event updated successfully."
    assert (
        calendar.CALENDAR_EVENTS.loc[calendar.CALENDAR_EVENTS["event_id"] == "70838584", "event_name"].values[0]
        == "New Event Name"
    )

    assert (
        call_tool(calendar.update_event, "70838584", "participant_email", "Updated@Company.com")
        == "Event updated successfully."
    )
    assert (
        calendar.CALENDAR_EVENTS.loc[calendar.CALENDAR_EVENTS["event_id"] == "70838584", "participant_email"].values[0]
        == "updated@company.com"
    )


def test_update_event_handles_missing_or_unknown_id():
    assert (
        call_tool(calendar.update_event, None, "event_name", "New Event Name")
        == "Event ID, field, or new value not provided."
    )
    assert call_tool(calendar.update_event, "00000000", "event_name", "New Event Name") == "Event not found."
