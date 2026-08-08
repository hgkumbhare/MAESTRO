"""Held-out fictional entities for leakage-safe micro-demos and generated examples.

These names / emails / ids must appear NOWHERE in the eval data. The audit gate
(experiments.common.audit) verifies disjointness; this module just provides the pool.
Reserved id range 90000000-90999999 is outside WorkBench's 000000xx range.
"""

# Fictional people (not in the WorkBench company directory).
SANDBOX_PEOPLE = [
    {"name": "Dana Ito", "email": "dana.ito@vertex.example"},
    {"name": "Priya Nair", "email": "priya.nair@northwind.example"},
    {"name": "Marco Silva", "email": "marco.silva@vertex.example"},
    {"name": "Lena Fischer", "email": "lena.fischer@northwind.example"},
    {"name": "Omar Haddad", "email": "omar.haddad@vertex.example"},
]

SANDBOX_EMAIL_DOMAINS = ["vertex.example", "northwind.example"]
SANDBOX_ID_RANGE = (90000000, 90999999)


def sandbox_task(task_id: str, name_idx: int, list_name: str = "In Progress",
                 board: str = "Design", task_name: str = "Draft spec",
                 due_date: str = "2023-09-01") -> dict:
    """Build one fictional project-task record assigned to a sandbox person."""
    person = SANDBOX_PEOPLE[name_idx % len(SANDBOX_PEOPLE)]
    return {
        "task_id": task_id,
        "task_name": task_name,
        "assigned_to_email": person["email"],
        "list_name": list_name,
        "due_date": due_date,
        "board": board,
    }
