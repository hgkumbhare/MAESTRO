import ast
from pathlib import Path

_ORIGINAL_TOOL_DESCRIPTIONS = {}
_SKILLS_CACHE = {}


def _get_tool_description(tool):
    return getattr(tool, "description", None) or getattr(tool, "__doc__", "") or ""


def _set_tool_description(tool, description):
    if hasattr(tool, "description"):
        try:
            print("congrats added dependency skill to tool description.")
            tool.description = description
        except AttributeError:
            print("Ohh no failed to add dependency skill to tool description.")
            pass
    try:
        tool.__doc__ = description
        print('Debug description with tool intraction skills {}'.format(description))
    except AttributeError:
        pass


def _get_tool_name(tool):
    """Extract the tool function name from a tool object."""
    if hasattr(tool, "name"):
        return tool.name
    if hasattr(tool, "__name__"):
        return tool.__name__
    if hasattr(tool, "func") and hasattr(tool.func, "__name__"):
        return tool.func.__name__
    return None


def _load_skills(skills_path):
    """Load the {tool_name: skill_description} mapping from the skills file."""
    source = Path(skills_path).read_text()
    skills = ast.literal_eval(source)
    if not isinstance(skills, dict):
        raise ValueError(f"Expected a dict of skills in {skills_path}, got {type(skills)}")
    return skills


def _build_dependency_skill_documentation(skill):
    """Build the documentation block appended to a tool's description."""
    if not skill:
        return ""
    return (
        "\n\nPRECONDITION: Read below carefully to understand tool dependencies and how to "
        "obtain each required input before calling this tool:\n\n" + skill
    )


def apply_tool_dependency_skills(tools, skills_path=None):
    """Append each tool's dependency skill to its description/docstring.

    Mirrors ``apply_integration_test_documentation``: original descriptions are
    cached per tool object so re-application is idempotent.
    """
    global _SKILLS_CACHE
    if not _SKILLS_CACHE:
        _SKILLS_CACHE = _load_skills(skills_path)

    for tool in tools:
        tool_key = id(tool)
        if tool_key not in _ORIGINAL_TOOL_DESCRIPTIONS:
            _ORIGINAL_TOOL_DESCRIPTIONS[tool_key] = _get_tool_description(tool)

        tool_name = _get_tool_name(tool)
        description = _ORIGINAL_TOOL_DESCRIPTIONS[tool_key]

        # Only add a skill if one is defined for this tool
        if tool_name and tool_name in _SKILLS_CACHE:
            skill = _SKILLS_CACHE[tool_name]
            print(f"Adding dependency skill for tool_name: '{tool_name}' and skill: '{skill}'")
            description += _build_dependency_skill_documentation(skill)
        else:
            print(f"No dependency skill found for tool '{tool_name}'")

        _set_tool_description(tool, description)

    return tools
