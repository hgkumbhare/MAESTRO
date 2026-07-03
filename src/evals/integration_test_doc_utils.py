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


INTEGRATION_TESTS = {
}

_ORIGINAL_TOOL_DESCRIPTIONS = {}
_TOOL_TESTS_CACHE = {}


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


def _extract_tool_calls_from_test(test_source):
    """
    Extract tool function names called in a test.
    Returns a set of tool names like: {'find_email_address', 'search_tasks', 'update_task'}
    """
    called_tools = set()
    try:
        tree = ast.parse(test_source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name):          # bare call: create_event(...)
                name = func.id
            elif isinstance(func, ast.Attribute):   # qualified: calendar.create_event(...)
                name = func.attr
            else:
                continue
            called_tools.add(name)
    except Exception as e:
        print(f"Error extracting tool calls from test: {e}")
    return called_tools


def _build_tool_to_tests_mapping(test_file_path):
    """
    Build a mapping of tool names to the tests that call them.
    Returns: {tool_name: [test_source1, test_source2, ...], ...}
    """
    tests_by_name = _get_test_source_by_name(test_file_path)
    tool_to_tests = {}
    
    for test_name, test_source in tests_by_name.items():
        called_tools = _extract_tool_calls_from_test(test_source)
        for tool_name in called_tools:
            if tool_name not in tool_to_tests:
                tool_to_tests[tool_name] = []
            tool_to_tests[tool_name].append(test_source)
    
    return tool_to_tests


def _get_tool_name(tool):
    """Extract the tool function name from a tool object."""
    if hasattr(tool, "name"):
        return tool.name
    if hasattr(tool, "__name__"):
        return tool.__name__
    if hasattr(tool, "func") and hasattr(tool.func, "__name__"):
        return tool.func.__name__
    return None


def _build_integration_test_documentation(test_sources):
    """Build documentation string from a list of test sources."""
    if not test_sources:
        return ""
    
    return "\n\nRead below carefully to understand tool dependency:\n\n" + "\n\n".join(
        f"```python\n{test_source}\n```" for test_source in test_sources
    )


def apply_integration_test_documentation(tools, integration_test_path):
    # Build tool-to-tests mapping once
    global _TOOL_TESTS_CACHE
    if not _TOOL_TESTS_CACHE:
        _TOOL_TESTS_CACHE = _build_tool_to_tests_mapping(integration_test_path)
    
    for tool in tools:
        tool_key = id(tool)
        if tool_key not in _ORIGINAL_TOOL_DESCRIPTIONS:
            _ORIGINAL_TOOL_DESCRIPTIONS[tool_key] = _get_tool_description(tool)

        tool_name = _get_tool_name(tool)
        description = _ORIGINAL_TOOL_DESCRIPTIONS[tool_key]
        
        # Only add integration tests if this tool is called in any test
        if tool_name and tool_name in _TOOL_TESTS_CACHE:
            test_sources = _TOOL_TESTS_CACHE[tool_name]
            print(f"Found {len(test_sources)} integration test(s) for tool '{tool_name}'")
            print("-------------Description before-------------\n", description)
            description += _build_integration_test_documentation(test_sources)
            print(f"Added integration test documentation for tool '{tool_name}'")
            print("-------------Description after-------------\n", description)
        else:
            print(f"No integration tests found for tool '{tool_name}'")

        _set_tool_description(tool, description)

    return tools
