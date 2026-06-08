import ast
from pathlib import Path

from tests.src.tools_improved_smolagents import test_calendar as test_smol_calendar_toolkit_improved


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
}

_ORIGINAL_TOOL_DESCRIPTIONS = {}


def _get_tool_description(tool):
    return getattr(tool, "description", None) or getattr(tool, "__doc__", "") or ""


def _set_tool_description(tool, description):
    if hasattr(tool, "description"):
        try:
            tool.description = description
        except AttributeError:
            pass
    try:
        tool.__doc__ = description
    except AttributeError:
        pass


def _get_test_source_by_name(test_module):
    test_file = Path(test_module.__file__)
    source = test_file.read_text()
    tree = ast.parse(source)
    tests = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test_source = ast.get_source_segment(source, node)
            if test_source:
                tests[node.name] = test_source
    return tests


def _build_unit_test_documentation(tool_name, test_module):
    tests_by_name = _get_test_source_by_name(test_module)
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
            description += _build_unit_test_documentation(tool_name, test_smol_calendar_toolkit_improved)
        _set_tool_description(tool, description)

    return tools
