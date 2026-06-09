import ast
from pathlib import Path
import sys
from unittest.mock import patch
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.evals.unit_test_doc_utils as doc_utils
from src.evals.unit_test_doc_utils import (
    apply_unit_test_documentation,
)


class DummyTool:
    def __init__(self, name=None, description=None, docstring=None):
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if docstring is not None:
            self.__doc__ = docstring


class ReadOnlyTool:
    @property
    def description(self):
        return "read-only-description"

    @property
    def __doc__(self):
        return "read-only-doc"


@pytest.fixture(autouse=True)
def clean_original_descriptions():
    doc_utils._ORIGINAL_TOOL_DESCRIPTIONS.clear()
    yield
    doc_utils._ORIGINAL_TOOL_DESCRIPTIONS.clear()


def test_apply_unit_test_documentation(tmp_path):
    # We'll create a dummy test file representing the test calendar module
    test_file = tmp_path / "dummy_test_calendar.py"
    test_content = """
def test_get_event_information_by_id_returns_requested_field():
    pass

def test_get_event_information_by_id_handles_missing_and_unknown_fields():
    pass
"""
    test_file.write_text(test_content)

    class MockModule:
        __file__ = str(test_file)

    # Let's mock the import of test_smol_calendar_toolkit_improved in apply_unit_test_documentation
    with patch("src.evals.unit_test_doc_utils.test_smol_calendar_toolkit_improved", MockModule):
        tool1 = DummyTool(name="get_event_information_by_id", description="Get event info.")
        tool2 = DummyTool(name="create_event", description="Create a new event.")
        tool3 = DummyTool(name="unmapped_tool", description="Unmapped tool.")

        tools = [tool1, tool2, tool3]

        # 1. Run with include_unit_tests=False
        result = apply_unit_test_documentation(tools, include_unit_tests=False)
        
        # Verify that tools lists are returned
        assert len(result) == 3
        # Descriptions should be their original descriptions
        assert tool1.description == "Get event info."
        assert tool2.description == "Create a new event."
        assert tool3.description == "Unmapped tool."

        # Verify caching of original descriptions
        assert id(tool1) in doc_utils._ORIGINAL_TOOL_DESCRIPTIONS
        assert doc_utils._ORIGINAL_TOOL_DESCRIPTIONS[id(tool1)] == "Get event info."
        assert id(tool2) in doc_utils._ORIGINAL_TOOL_DESCRIPTIONS
        assert doc_utils._ORIGINAL_TOOL_DESCRIPTIONS[id(tool2)] == "Create a new event."
        # Unmapped tool should NOT be cached
        assert id(tool3) not in doc_utils._ORIGINAL_TOOL_DESCRIPTIONS

        # 2. Run with include_unit_tests=True
        # For tool1, it should append the unit test documentation
        # For tool2, the tests are not in MockModule, so it shouldn't append anything (or append empty string)
        # For tool3, it is unmapped so it shouldn't change
        result = apply_unit_test_documentation(tools, include_unit_tests=True)
        
        assert "Behavior verified by unit tests:" in tool1.description
        assert "test_get_event_information_by_id_returns_requested_field" in tool1.description
        
        # tool2 description remains unchanged because no matching tests were defined in MockModule
        assert tool2.description == "Create a new event."
        assert tool3.description == "Unmapped tool."

        # 3. Call again with include_unit_tests=False
        # It should restore tool1 description to original
        apply_unit_test_documentation(tools, include_unit_tests=False)
        assert tool1.description == "Get event info."
