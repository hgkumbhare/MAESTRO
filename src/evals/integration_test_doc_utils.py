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
_INTEGRATION_TEST_PATH = _TESTS_DIR / "test_integration_tests.py"


INTEGRATION_TESTS = {
}

_ORIGINAL_TOOL_DESCRIPTIONS = {}


def _get_tool_description(tool):
    return getattr(tool, "description", None) or getattr(tool, "__doc__", "") or ""


def _set_tool_description(tool, description):
    if hasattr(tool, "description"):
        try:
            print("congrats added integration tests to tool description.")
            tool.description = description
        except AttributeError:
            print("Ohh no failed to add integration tests to tool description.")
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


def _build_integration_test_documentation(test_file_path):
    tests_by_name = _get_test_source_by_name(test_file_path)

    return "\n\nBehavior verified by integration tests:\n\n" + "\n\n".join(
        f"```python\n{test_source}\n```" for test_source in tests_by_name.values()
    )


def apply_integration_test_documentation(tools):
    for tool in tools:
        tool_key = id(tool)
        if tool_key not in _ORIGINAL_TOOL_DESCRIPTIONS:
            _ORIGINAL_TOOL_DESCRIPTIONS[tool_key] = _get_tool_description(tool)

        description = _ORIGINAL_TOOL_DESCRIPTIONS[tool_key]
        print('Previous description: ', description)
        description += _build_integration_test_documentation(_INTEGRATION_TEST_PATH)
        print('Updated description added integration tests: ', description)
        _set_tool_description(tool, description)

    return tools
