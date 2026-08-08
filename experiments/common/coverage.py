"""Template-coverage map: which PM eval templates have a matching integration test.

Used as the leakage "honesty meter" — gains on COVERED templates are suspect
(memorization); gains on UNCOVERED templates are real within-dataset generalization.
See docs/paper_review.md S3.
"""

# Substrings that identify the 5 PM base_templates that HAVE an integration test.
COVERED_KEYS = [
    "in progress to in review",
    "overdue tasks in the backlog to in progress",
    "in review to completed",
    "sick so reassign",
    "unfinished tasks to the backlog",
]


def coverage(base_template) -> str:
    """Return 'covered' if the template has a matching integration test, else 'uncovered'."""
    t = str(base_template).lower()
    return "covered" if any(k in t for k in COVERED_KEYS) else "uncovered"
