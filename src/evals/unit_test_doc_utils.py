import ast
from pathlib import Path

# Reference the unit-test sources by path rather than importing them. The test
# modules install a stub into ``sys.modules["smolagents"]`` at import time for
# their own isolation; importing them here would poison the real ``smolagents``
# package for the whole process (breaking ``CodeAgent``). We only need the
# source text to extract test bodies, so read the files directly.
_TESTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "src"
    / "tools_improved_smolagents"
)
_TEST_CALENDAR_PATH = _TESTS_DIR / "test_calendar.py"
_TEST_PROJECT_MANAGEMENT_PATH = _TESTS_DIR / "test_project_management.py"


UNIT_TESTS_BY_TOOL = {
    "get_event_information_by_id": [
        "test_get_event_information_by_id_returns_requested_field",
        "test_get_event_information_by_id_handles_missing_and_unknown_fields",
    ],
    "search_events": [
        "test_search_events_matches_name_or_email_case_insensitively",
        "test_search_events_filters_by_time_range",
        "test_search_events_returns_message_when_no_events_match",
        "test_search_events_limits_results_to_five",
    ],
    "create_event": [
        "test_create_event_appends_event_and_normalizes_email",
        "test_create_event_validates_required_arguments",
    ],
    "delete_event": [
        "test_delete_event_removes_existing_event",
        "test_delete_event_handles_missing_or_unknown_id",
    ],
    "update_event": [
        "test_update_event_changes_field_and_normalizes_email",
        "test_update_event_handles_missing_or_unknown_id",
    ],
    "get_task_information_by_id": [
        "test_get_task_information_by_id_returns_requested_field",
        "test_get_task_information_by_id_missing_task_id",
        "test_get_task_information_by_id_missing_field",
        "test_get_task_information_by_id_unknown_field",
        "test_get_task_information_by_id_unknown_task",
    ],
    "search_tasks": [
        "test_search_tasks_no_parameters",
        "test_search_tasks_partial_case_insensitive_name",
        "test_search_tasks_multiple_fields_are_anded",
        "test_search_tasks_returns_full_records",
        "test_search_tasks_no_matches_returns_empty_list",
    ],
    "create_task": [
        "test_create_task_appends_and_returns_new_id_and_lowercases_email",
        "test_create_task_missing_details",
        "test_create_task_invalid_assignee",
        "test_create_task_invalid_list_name",
        "test_create_task_invalid_board",
    ],
    "delete_task": [
        "test_delete_task_removes_existing_task",
        "test_delete_task_missing_id",
        "test_delete_task_unknown_id",
    ],
    "update_task": [
        "test_update_task_changes_field",
        "test_update_task_normalizes_email",
        "test_update_task_missing_parameters",
        "test_update_task_invalid_board",
        "test_update_task_invalid_list_name",
        "test_update_task_invalid_assignee",
        "test_update_task_unknown_field",
        "test_update_task_unknown_task",
    ],
}

# Maps each tool to the test file whose source defines its unit tests.
_TEST_FILE_BY_TOOL = {
    "get_event_information_by_id": _TEST_CALENDAR_PATH,
    "search_events": _TEST_CALENDAR_PATH,
    "create_event": _TEST_CALENDAR_PATH,
    "delete_event": _TEST_CALENDAR_PATH,
    "update_event": _TEST_CALENDAR_PATH,
    "get_task_information_by_id": _TEST_PROJECT_MANAGEMENT_PATH,
    "search_tasks": _TEST_PROJECT_MANAGEMENT_PATH,
    "create_task": _TEST_PROJECT_MANAGEMENT_PATH,
    "delete_task": _TEST_PROJECT_MANAGEMENT_PATH,
    "update_task": _TEST_PROJECT_MANAGEMENT_PATH,
}

_ORIGINAL_TOOL_DESCRIPTIONS = {}


def _get_tool_description(tool):
    return getattr(tool, "description", None) or getattr(tool, "__doc__", "") or ""


def _set_tool_description(tool, description):
    if hasattr(tool, "description"):
        try:
            print("congrats added unit tests to tool description.")
            tool.description = description
        except AttributeError:
            print("Ohh no failed to add unit tests to tool description.")
            pass
    try:
        tool.__doc__ = description
    except AttributeError:
        pass


def _get_test_source_by_name(test_file_path):
    test_file = Path(test_file_path)
    source = test_file.read_text()
    tree = ast.parse(source)
    tests = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test_source = ast.get_source_segment(source, node)
            if test_source:
                tests[node.name] = test_source
    return tests


def _build_unit_test_documentation(tool_name, test_file_path):
    tests_by_name = _get_test_source_by_name(test_file_path)
    test_sources = [
        tests_by_name[test_name]
        for test_name in UNIT_TESTS_BY_TOOL.get(tool_name, [])
        if test_name in tests_by_name
    ]
    if not test_sources:
        return ""

    return "\n\nBehavior verified by unit tests:\n\n" + "\n\n".join(
        f"```python\n{test_source}\n```" for test_source in test_sources
    )


def apply_unit_test_documentation(tools, include_unit_tests=False):
    for tool in tools:
        tool_name = getattr(tool, "name", None)
        if tool_name not in UNIT_TESTS_BY_TOOL:
            continue

        tool_key = id(tool)
        if tool_key not in _ORIGINAL_TOOL_DESCRIPTIONS:
            _ORIGINAL_TOOL_DESCRIPTIONS[tool_key] = _get_tool_description(tool)

        description = _ORIGINAL_TOOL_DESCRIPTIONS[tool_key]
        if include_unit_tests:
            print('Previous description: ', description)
            test_file_path = _TEST_FILE_BY_TOOL.get(tool_name, _TEST_CALENDAR_PATH)
            description += _build_unit_test_documentation(tool_name, test_file_path)
            print('Updated description: ', description)
        _set_tool_description(tool, description)

    return tools
