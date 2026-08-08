# WorkBench + Integration Tests — How It Works Today

A ground-truth explainer of (1) what the WorkBench benchmark is, (2) how the
"integration test" mechanism is built and injected **right now**, (3) what the tests
actually look like, and (4) the coverage problem — with a concrete before/after
example. Everything here is reconstructed from the code, with links.

---

## 1. What is WorkBench?

WorkBench (Styles et al., 2024) is a sandboxed benchmark for evaluating LLM agents on
realistic workplace tasks. This repo forks it.

- **5 domains**, each backed by a CSV "database": Calendar, Email, Analytics,
  Project Management, CRM (+ a small Company-Directory helper).
- **~26–27 tools** total (LangChain `@tool` functions) — see inventory below.
- **690 tasks** (query → expected outcome), e.g. *"Delete my first meeting on Dec 13."*
- **Outcome-based evaluation.** Each task has a **unique, unambiguous** correct
  outcome. The harness resets the databases, runs the agent, then checks whether the
  agent's tool calls produced the same database change as the ground-truth calls.
  Tools are split into **side-effecting** (mutate a DB) and **read-only**, so the eval
  can also flag *wrong* mutations ("unwanted side effects").

### Tool inventory (from [src/tools/toolkits.py](../src/tools/toolkits.py))

| Domain | Side-effecting tools | Read-only tools | Total |
|---|---|---|---|
| Calendar | create_event, delete_event, update_event | get_event_information_by_id, search_events | 5 |
| Email | send_email, delete_email, forward_email, reply_email | get_email_information_by_id, search_emails | 6 |
| Analytics | create_plot | engaged_users_count, get_visitor_information_by_id, traffic_source_count, total_visits_count, get_average_session_duration | 6 |
| Project Mgmt | create_task, delete_task, **update_task** | get_task_information_by_id, **search_tasks** | 5 |
| CRM | update_customer, add_customer, delete_customer | search_customers | 4 |
| Company Directory | — | **find_email_address** | 1 |
| **Total** | | | **27** |

Bold = the only tools currently touched by an integration test (see §4).

---

## 2. How an "integration test" is made right now

There are **two stages**, and they are easy to conflate.

### Stage A — Authoring (manual / offline; NOT in the code path)
The tests are **hand-written pytest functions** in
[tests/src/tools_improved_smolagents/test_integration_tests.py](../tests/src/tools_improved_smolagents/test_integration_tests.py).
The prompt on **p.8 of the paper** ("Create 5–10 new integration tests… Output only the
Python integration tests") is the *intended* LLM recipe for producing them — but that
generation is **not wired into the pipeline**. Someone writes/generates the tests
offline and saves the file; the code only consumes it.

### Stage B — Injection into the prompt
Done by `apply_integration_test_documentation(tools)` in
[src/evals/integration_test_doc_utils.py](../src/evals/integration_test_doc_utils.py),
at toolkit-build time:

```
test_integration_tests.py
        │
        ▼
1. Read file source, AST-parse it
   _get_test_source_by_name()  → {test_name: full source of `def test_*`}
        │
        ▼
2. For each test, find which tools it "calls"
   _extract_tool_calls_from_test(): walk AST, grab every `X.attr`
   attribute access → treat `attr` as a tool name
   e.g.  project_management.search_tasks  →  "search_tasks"
        │
        ▼
3. Build mapping   {tool_name: [test_source, ...]}
        │
        ▼
4. For each tool in the toolkit:
     if tool.name ∈ mapping:
         tool.description +=
             "\n\nBehavior verified by integration tests:\n\n"
             + ```python <full test function source> ```
     else:
         (description unchanged)
```

**Net effect:** the verbatim source of every test that mentions a tool is appended to
that tool's description string. That augmented description is what the ReAct agent
reads in its tool list. Nothing is executed or verified at inference time — the test
*text* is used purely as in-context (few-shot) examples.

---

## 3. What the tests look like right now

All 5 tests live in
[test_integration_tests.py](../tests/src/tools_improved_smolagents/test_integration_tests.py):

| # | Test | Domain | Real tools exercised |
|---|---|---|---|
| 1 | [test_move_in_progress_tasks_to_in_review](../tests/src/tools_improved_smolagents/test_integration_tests.py#L39) | PM | find_email_address, search_tasks, update_task |
| 2 | [test_integration_move_all_overdue_backlog_tasks_to_in_progress](../tests/src/tools_improved_smolagents/test_integration_tests.py#L87) | PM | search_tasks, update_task |
| 3 | [test_integration_move_any_review_tasks_to_completed](../tests/src/tools_improved_smolagents/test_integration_tests.py#L147) | PM | search_tasks, update_task |
| 4 | [test_integration_reassign_yukis_in_progress_tasks_to_carlos](../tests/src/tools_improved_smolagents/test_integration_tests.py#L204) | PM | find_email_address, search_tasks, update_task |
| 5 | [test_integration_move_unfinished_tasks_to_backlog](../tests/src/tools_improved_smolagents/test_integration_tests.py#L271) | PM | search_tasks, update_task |

A representative test (test #1) — note it is a real pytest with setup, helper calls,
and `assert`s, not a clean demonstration:

```python
def test_move_in_progress_tasks_to_in_review():
    set_tasks([
        {"task_id": "00000042", "task_name": "Prepare Q3 product launch plan",
         "assigned_to_email": "aisha.chen@atlas.com", "list_name": "In Progress",
         "due_date": "2023-09-01", "board": "Design"},
        {"task_id": "00000043", "task_name": "Final Launch",
         "assigned_to_email": "aisha.chen@atlas.com", "list_name": "Backlog",
         "due_date": "2023-09-01", "board": "Design"},
    ])
    # Inputs: Move all of Aisha's tasks that are in progress to in review
    name = 'Aisha'
    current_list_name = "In Progress"
    updated_list_name = "In Review"

    # tool calling
    emails = call_tool(company_directory.find_email_address, name)
    assert len(emails) == 1
    assert "aisha.chen@atlas.com" in emails

    email_id = str(emails[0])
    results = call_tool(project_management.search_tasks,
                        assigned_to_email=email_id, list_name=current_list_name)
    assert len(results) == 1
    assert results[0]["task_id"] == "00000042"

    update_message = call_tool(project_management.update_task,
                               "00000042", "list_name", updated_list_name)
    assert update_message == "Task updated successfully."
    # ... asserts the DB row was actually updated
```

The *teaching signal* buried in here is good: **find email → search tasks by that email
→ update the found task** (a genuine multi-step dependency chain). But it is wrapped in
`set_tasks(...)`, `call_tool(...)`, and assertions that are pytest plumbing, not
guidance for the model.

---

## 4. What gets injected — a concrete before/after

Tool: `project_management.search_tasks`
(original definition:
[src/tools/project_management.py#L44](../src/tools/project_management.py#L44)).

**BEFORE** (what the agent sees in the `original` tool set):

```
Searches for tasks based on the given parameters.

Args:
    task_name: Name of the task.
    assigned_to_email: Email address of the person assigned to the task.
    list_name: Name of the list the task belongs to.
    due_date: Due date of the task in "YYYY-MM-DD" format.
    board: Name of the board the task belongs to.

Examples:
>>> project_management.search_tasks("Refactor code", "tishtrya@example.com" ...)
{"task_id": "00000000", "task_name": "Refactor code", ...}
```

**AFTER** (`improved` + integration tests): the same text, plus an appended block. Because
**all 5 tests call `search_tasks`**, this one tool gets **all five full test functions**
(~250 lines of pytest) stapled onto its description:

```
...original description above...

Behavior verified by integration tests:

```python
def test_move_in_progress_tasks_to_in_review():
    set_tasks([...])
    ...
    emails = call_tool(company_directory.find_email_address, name)
    results = call_tool(project_management.search_tasks, ...)
    update_message = call_tool(project_management.update_task, ...)
    ...
```

```python
def test_integration_move_all_overdue_backlog_tasks_to_in_progress():
    ... (another full test) ...
```
... (three more full tests) ...
```

So the most-covered tool balloons with 5 verbatim pytest bodies, while 24 of 27 tools
get **nothing**.

---

## 5. The problem

1. **Coverage is tiny and skewed.** The 5 tests touch **3 real tools**
   (`search_tasks`, `update_task`, `find_email_address`) = **~11% of 27 tools**, across
   effectively **1 domain** (Project Management). 24 tools and 4 domains receive no
   examples at all. This mechanically explains the Table 2 pattern (PM improves; other
   domains flat).

2. **5–10 tests cannot cover all APIs.** With ~2–3 tools per test, even 10
   non-overlapping tests reach ~20–30 tools — barely one pass over WorkBench, and
   hopeless for API-Bank (2,138 APIs). A per-tool-coverage strategy does not scale, and
   inherits the very cost problem the paper criticizes in fine-tuning.

3. **The extraction is noisy.** `_extract_tool_calls_from_test` treats *every* `Name.attr`
   as a tool name, so it also collects junk like `atlas.com`, `sys.modules`,
   `importlib.import_module`, `tool_obj.forward`. Harmless only because junk names rarely
   equal real tool names — but fragile and undocumented.

4. **Injected content is noisy pytest, not clean demos.** The model receives
   `set_tasks(...)`, `call_tool(...)`, and `assert`s. The useful dependency chain is
   present but diluted.

5. **"Integration test" is a misnomer for the mechanism.** Nothing is executed or
   validated at inference — test *source* is used as few-shot text. The paper's framing
   ("validate tool calls against executable specifications," "corrective feedback")
   describes a system that is not implemented.

6. **Can't separate "covered" from "generalized."** Because only treated tools improved,
   the results cannot show whether behavioral examples **transfer** to untouched tools —
   which is the paper's actual scientific claim.

7. **Template/procedure leakage (CONFIRMED).** The bigger problem than coverage: the
   tests demonstrate the gold solution for the **same task templates the eval grades
   on.** PM eval = 8 templates × 10 queries. **5 of the 8 templates have a matching
   integration test:**

   | Integration test | Eval template (10 queries) |
   |---|---|
   | move_in_progress_tasks_to_in_review | "Move all of {name}'s tasks that are in progress to in review" |
   | move_all_overdue_backlog_tasks_to_in_progress | "Move all of {name}'s overdue tasks in the backlog to in progress" |
   | move_any_review_tasks_to_completed | "Move any of {name}'s tasks that are in review to completed" |
   | reassign_yukis_in_progress_tasks_to_carlos | "{name_1} is sick so reassign their in progress tasks to {name_2}" |
   | move_unfinished_tasks_to_backlog | "{name_1} is on vacation now so move all their unfinished tasks to the backlog" |
   | *(uncovered)* | "Add a new task to the {board} backlog…" |
   | *(uncovered)* | "Give all the overdue tasks that {name_1} hasn't started to {name_2}" |
   | *(uncovered)* | "Take {name_1}'s most urgent task and reassign it to {name_2}" |

   Plus **entity overlap**: test #1 uses "Aisha" (eval has an Aisha query); test #4 uses
   "Yuki→Carlos" and **Yuki is a real eval entity** (task_id 00000091). This is not raw
   answer-string leakage (synthetic task_ids differ), but **procedure/template
   leakage** — the PM gain (47.5→60) may just be memorized in-distribution solutions.

### The fork in the road
- **Coverage story** — write a test per tool. Doesn't scale; weak.
- **Generalization story** — a few examples teach transferable tool-interaction
  *patterns* that help **untouched** tools. Interesting, publishable — but **requires a
  held-out-tool experiment** that is not yet done.

### Built-in control we already have
3 of the 8 PM templates are **uncovered** by any test. Split PM accuracy by
**covered (5)** vs **uncovered (3)** templates:
- gains only on covered → leakage/memorization;
- gains on uncovered too → real generalization (defensible).

See [paper_review.md](./paper_review.md) issues **C1, C3, C4, S3** for linked actions.
