# Retrieval-Based Behavioral Examples — Target Design

The proposed upgrade from the current mechanism (5 static integration tests stapled
onto tool descriptions) to a **large bank of behavioral examples retrieved per query**.
This resolves the coverage, prompt-bloat, and leakage problems in one design, and turns
the paper's central hypothesis into something measurable.

Related docs: [workbench_and_integration_tests.md](./workbench_and_integration_tests.md)
(how it works today) · [paper_review.md](./paper_review.md) (issue tracker: C2, C3, C4, S3).

---

## 1. Motivation

**Hypothesis:** behavioral usage examples help the model infer correct tool
interactions (right tool, right order, right parameters, reuse of returned values).

**Why 5 static examples are not enough:**
- **Coverage:** 5 tests touch 3 of 27 tools (~11%), one domain. Cannot cover all tools;
  hopeless for API-Bank (2,138 APIs).
- **Prompt bloat:** you cannot just add 50 static examples — one tool already receives 5
  full pytest bodies. Static injection trades coverage against prompt size.
- **Leakage:** static tests mirror eval templates → memorization, not skill (see S3).

**Key realization:** decouple *how many examples exist* from *how many enter the prompt.*
Keep a **large bank**, inject only the **top-k most relevant** per query via embeddings.

---

## 2. Architecture

```
        BUILD TIME (offline)                      INFERENCE TIME (per query)
   ┌──────────────────────────┐             ┌──────────────────────────────┐
   │  Example bank (100s)      │             │  user query                  │
   │  each record:             │             │       │ embed                │
   │   - scenario text         │             │       ▼                      │
   │   - tool chain            │  embed all  │  cosine sim vs bank index    │
   │   - clean demo            │────────────▶│       │                      │
   │   - skill/failure tag     │   FAISS     │  top-k (3–5), leakage-guard  │
   │   - source entities       │◀────────────│       ▼                      │
   │       │                   │   query     │  inject "relevant worked     │
   │       ▼                   │             │  examples" block into        │
   │  vector index (FAISS)     │             │  system prompt → ReAct agent │
   └──────────────────────────┘             └──────────────────────────────┘
```

This is **dynamic few-shot / demonstration retrieval** applied to tool-interaction
examples. It mirrors the paper's own **"Search API"** idea (§2: cosine similarity over
API metadata) — here pointed at *examples* instead of tool metadata, so it is a natural,
already-motivated extension.

**Available in-repo:** `requirements.txt` already ships `faiss-cpu`,
`sentence-transformers`, and `langchain` — the full stack. No new heavy dependency.

---

## 3. What it fixes

| Problem (today) | How retrieval fixes it |
|---|---|
| Coverage 3/27 tools | Bank can cover every tool / API; index scales freely |
| Prompt bloat (5 tests on one tool) | Constant-size prompt: only top-k injected |
| Generic, irrelevant examples | Query-matched examples, most relevant first |
| Doesn't scale to API-Bank | Index handles thousands of APIs; retrieval stays O(k) |

---

## 4. The leakage guard (critical)

Retrieval **amplifies** leakage if the bank is not disciplined: for each eval query the
nearest neighbor could be the near-identical worked solution → the system becomes an
**answer-key lookup table**, and reported gains are pure memorization.

**Mandatory rules for the bank:**
1. **Disjoint from the eval set.** Bank scenarios use held-out entities, phrasings, and
   IDs that appear nowhere in WorkBench / API-Bank.
2. **Retrieval-time leakage guard.** Reject any retrieved example whose template or
   entities overlap the current query.
3. **Report overlap metrics.** Quantify and publish bank↔eval overlap (should be ~0).

**The upside:** a **disjoint bank + retrieval that still improves accuracy is clean,
strong evidence of generalization** (C4) — because nothing retrieved was a solution to
the graded task. This converts the project's biggest weakness (S3 leakage) into its
headline result.

---

## 5. Building the example bank

### 5.1 Skill taxonomy & failure modes

**Terminology:** a *failure mode* is a way the model goes wrong (a hallucination type);
a *skill* is the competence that prevents it — what a behavioral example teaches. Every
failure mode maps to a skill. The bank is **organized by skills**, but each example also
tags the `failure_mode_targeted` it addresses, so results can be broken down per mode
later (S5).

**Full taxonomy (paper §2.1) — 3 categories, ~12 failure modes.** Use this for
*diagnosis / error analysis*:

- **Tool Selection Hallucination**
  1. confident response without invoking any required tool
  2. executing tools in the wrong sequence
  3. duplicate / unnecessary tool calls
  4. invokes a non-existent tool
  5. invokes an irrelevant tool
- **Tool Calling Hallucination**
  6. syntactically invalid tool calls
  7. incorrect / omitted / fabricated parameters
  8. incorrect, default, or fabricated arguments
  9. using stale information from previous turns
- **Tool Result Hallucination**
  10. invokes the tool but ignores its output
  11. misinterprets the output
  12. doesn't wait for the output

**The count is a design choice** — you may split or merge these. Keep all 12 for
*diagnosis*, but build the bank around the subset that behavioral examples can actually
teach.

**Teachable subset → skills (build the bank around these ~6–7):**

| Failure mode(s) | Skill the example teaches | Teachable by example? |
|---|---|---|
| wrong sequence / broken dependency chain (2) | order tools; feed A's output into B | ✅ core case |
| fabricated parameters / arguments (7, 8) | fetch a value before using it; never invent IDs | ✅ |
| duplicate / unnecessary calls (3) | reuse a result you already have | ✅ |
| no tool when one is required (1) | recognize a task needs a tool | ✅ |
| wrong / irrelevant / non-existent tool (4, 5) | select the right tool (contrastive right-vs-wrong) | ✅ |
| ignores tool output (10) | read and use the returned value | ✅ |
| syntactically invalid calls (6) | correct call format / schema | ⚠️ partly (format issue) |
| misinterprets output (11) | — | ❌ reasoning, not demonstrable |
| stale info / doesn't wait (9, 12) | — | ❌ mostly multi-turn; N/A single-turn |

The ✅ rows are the skill taxonomy the example bank should cover. Each is teachable with
a **held-out, leakage-safe** scenario (see §6), ideally a task/domain that is *not* an
eval template so that improvement on eval tasks is genuine generalization (C4).

### 5.2 Example record schema

Each record:

```json
{
  "id": "chain_resolve_then_update_001",
  "scenario": "Reschedule Priya Nair's onboarding task to next sprint.",
  "skill": "dependency-chaining / reuse-returned-value",
  "failure_mode_targeted": "fabricated parameters",
  "tools": ["find_email_address", "search_tasks", "update_task"],
  "demo": "<clean step-by-step demonstration with concrete held-out values>",
  "entities": ["Priya Nair", "priya.nair@northwind.example", "00000777"],
  "executed_ok": true
}
```

Construction principles (see also the authoring guide in
[workbench_and_integration_tests.md](./workbench_and_integration_tests.md)):
- **Taxonomy-driven, not per-tool.** Cover the failure modes from paper §2.1 (wrong
  selection, broken dependency chain, fabricated params, duplicate calls, ignored
  output, missing info). ~N examples per failure mode across varied tools.
- **Execute-then-store.** Run each example against the real tools; only add ones that
  pass. This (a) guarantees valid demos and (b) legitimizes the "executable
  specification" framing (addresses C2 overclaim).
- **Clean demonstration format.** Request → reasoning → concrete tool calls → returned
  values → one-line "what this teaches" + a contrastive WRONG line. No pytest
  scaffolding (`set_tasks`, `call_tool`, `assert`) in the injected text.
- **Held-out entities only.** e.g. `Priya Nair`, `northwind.example` — absent from all
  benchmarks.

---

## 6. Leakage-safe construction & the audit gate

### 6.1 Two orthogonal leakage axes
An example leaks if it overlaps the eval on **either** axis — both must be checked:

| | Same task template | Different task template |
|---|---|---|
| **Same entities** | worst — full leak | caught by **entity blocklist** |
| **Different entities** | caught by **eval-query set** | ✅ clean |

- **Entity blocklist** = exact-value overlap (names, emails, IDs from `data/processed/`).
  Catches "different task, same values."
- **Eval-query set** = task/structure overlap. Catches "same task, different values" —
  e.g. *"Move all of Priya Nair's in-progress tasks to review"* uses a fictional name
  (passes the blocklist) but reproduces a graded template. Rewording does not help.

### 6.2 The litmus test (for humans and generators)
> **Mask all entities. Is the task one of the eval templates (or a paraphrase)?**
> Yes → it leaks, however reworded. No → legitimately different task, safe to teach.

Teach the *skill*, not the *task*. The transferable skill in
find→search→update is "resolve an identifier before acting; reuse the returned value."
Teach it with a task that is **not** an eval template — ideally a different operation or
domain (e.g. *"find the owner of calendar event #A47 and email them a reminder"*). If
training on such tasks still lifts PM task-moving (never demonstrated), that is genuine
generalization (C4).

### 6.3 The audit gate — `check_example(candidate) -> {leaks, reasons}`
The generator is **not** trusted to stay clean; the gate is the guarantee. A candidate
passes only if it clears **all** checks:

1. **Entity check (exact).** Extract every entity from `data/processed/*.csv` + all eval
   queries → blocklist set. Reject if the candidate contains any blocklisted
   name/email/ID. Deterministic, airtight.
2. **Template check (normalized).** Mask entities in the candidate task (`{name}`,
   `{email}`, `{id}`) and reject if it equals any eval `base_template`.
3. **Semantic check (embedding).** Embed the candidate task; reject if max cosine
   similarity to any of the 690 eval queries exceeds a threshold (~0.8). Catches
   reworded-but-same-task paraphrases.
4. **Answer/outcome check (exact).** Reject if the candidate's tool-call sequence over
   its values reproduces any eval ground-truth answer.

Run the gate at **build time** (filter the bank) **and** at **retrieval time** (never
inject an example that overlaps the current query). Report the resulting overlap stats
(entity-intersection = 0; similarity distribution) in the paper.

### 6.4 Construction pipeline (generate blind → filter)
Do **not** author examples by looking at eval items and permuting them — that anchors on
the eval distribution and produces paraphrases (high reject rate, residual leak risk).
Instead generate **blind to the eval set**, from skills + tool specs over a fictional
sandbox, then let the gate filter:

1. **Skill/failure-mode taxonomy** (paper §2.1): wrong selection, broken dependency
   chain, fabricated params, duplicate calls, ignored output, missing info.
2. **Held-out sandbox**: a parallel DB of fictional entities (fake company/people/IDs),
   same tool schema. All example values come from here.
3. **Generate blind**: for each skill, produce candidate examples from the *tool specs*
   and sandbox only — never conditioned on eval queries. **Over-generate** (the gate
   will drop some).
4. **Execute-then-store**: run each candidate against the tools; keep only passing ones
   (valid demos + real traces; also legitimizes "executable specification", C2).
5. **Audit gate (§6.3)**: drop any candidate that leaks on any axis.
6. **Dedup + embed** survivors → FAISS bank.

Because generation is seeded by skills + a disjoint sandbox (not eval permutations), the
expected reject rate is low — the gate is a safety net, not the primary filter. This is a
one-time offline pipeline and scales by over-generation, unlike hand-writing a test per
tool.

---

## 7. Retrieval design choices

| Decision | Options | Default to start |
|---|---|---|
| Match key | query ↔ scenario text; OR route-to-tools first, then retrieve by tool | query ↔ scenario |
| Embedding model | any `sentence-transformers` model (e.g. all-MiniLM) | small + fast first |
| k (examples injected) | 0 / 1 / 3 / 5 | ablate; start k=3 |
| Injection site | one "relevant worked examples" block in system prompt | system prompt block |
| Leakage guard | template/entity overlap filter | mandatory |

---

## 8. Experiment plan

1. **Held-out generalization (the headline).** Disjoint bank; evaluate on WorkBench /
   API-Bank. If accuracy rises with zero bank↔eval overlap → generalization (C4).
2. **k-ablation.** k ∈ {0,1,3,5}; find the point of diminishing returns. k=0 is the
   base condition — free baseline (C3).
3. **Bank-size ablation.** Grow the bank (25/50/100/…); does accuracy scale with bank
   size? Evidence that more behavioral coverage helps.
4. **Retrieval vs random vs static.** Compare retrieved top-k against (a) random k from
   the bank and (b) today's static 5. Isolates the value of *relevance* (C3 control).
5. **Per-failure-mode breakdown.** Tie gains to the taxonomy (paper §2.1) — which
   hallucination types drop? (addresses S5.)
6. **Multi-model.** Repeat on ≥2–3 models the repo supports (gpt-4o, llama, qwen) to
   support the "adaptable to any model" claim (S1).

---

## 9. Relationship to the current experiment

The running covered-vs-uncovered PM split is the **motivation** for this design:
- If gains concentrate on covered templates → static tests memorize → we *need* a
  disjoint retrieval bank to make an honest generalization claim.
- The retrieval design's held-out evaluation (§7.1) is the scaled-up, leakage-safe
  version of that same test.

---

## 10. The design space: injectable unit × taxonomy source (2×2)

Two **independent** design axes. Any combination is valid; they can also be blended.

- **Axis A — what you inject (the unit):**
  - **Examples (episodic):** concrete worked demonstrations. Teach by imitation. Strong
    grounding; higher leakage risk; one demo ≈ one task type.
  - **Skills (semantic):** abstract rule/procedure "skill cards." Teach by instruction.
    Near-zero leakage; one skill covers all tools matching a pattern; weaker grounding.
- **Axis B — how you build the failure taxonomy:**
  - **Top-down (hardcoded):** hand-author the failure modes (e.g. paper §2.1). Free, no
    base-model run, transfers across datasets. Risk: misses failures you didn't imagine.
  - **Bottom-up (empirical):** run the base model, cluster its actual errors, derive the
    taxonomy from observed failures (ExpeL / Reflexion lineage). Grounded in reality;
    costs a base-model run per domain family.

### The four quadrants

| | **Top-down taxonomy** | **Bottom-up taxonomy** |
|---|---|---|
| **Examples** | **Q1.** Hand-define modes → author held-out examples per mode. (Closest to current method, but leakage-fixed.) | **Q2.** Run base → cluster errors → generate examples targeting observed failures. |
| **Skills** | **Q3.** Hand-define taxonomy → author skill cards per mode. Most scalable + leakage-safe. **→ E1.** | **Q4.** Run base → cluster errors → distill skills/insights (ExpeL-style). Most grounded. **→ E8.** |

### Per-quadrant tradeoffs

| Quadrant | Leakage | Scales to new data | Grounding | Upfront cost | Prior-work anchor |
|---|---|---|---|---|---|
| Q1 Examples×Top-down | medium (audit needed) | medium | high | low | few-shot ICL |
| Q2 Examples×Bottom-up | medium (audit needed) | low (base run/dataset) | high | high | demo retrieval + error mining |
| Q3 Skills×Top-down | **near-zero** | **high** | medium | low | tool docs / SOP / constitution |
| Q4 Skills×Bottom-up | near-zero | medium (base run) | high | high | **ExpeL, Reflexion** |

### Scalability note (bottom-up)
Failure *modes* are largely **dataset-agnostic** (fabricated id, wrong sequence, ignored
output are universal). So a bottom-up taxonomy is a **build-once, reuse-everywhere**
artifact — not re-derived per dataset. It is an **offline, one-time cost per domain
family**, never an inference-time cost. On a new dataset the existing taxonomy runs
**zero-shot**; a fresh base-model pass is an *optional* refinement, and can be automated
(LLM clusters errors → proposes skills). Therefore bottom-up does **not** break
deployment scalability.

### Recommendation
- **Default: Q3 (Skills × Top-down)** — scalable, leakage-safe, faithful to the paper's
  "teach tool interaction" thesis, no base-model run.
- **Ground weak models** by attaching one **held-out micro-example** to each skill card
  (a touch of Q1) — best of both.
- **Refine with Q4** only when entering a new domain or when top-down coverage looks
  thin — optional, offline, automatable.
- Keep **Q2** mainly as a research comparison point (it inherits the leakage + scaling
  costs of examples *and* the base-run cost of bottom-up).

### Third axis: transfer scope (within-dataset vs cross-dataset)

A third dimension — **where a learned skill is applied**: the same benchmark it was built
on, or a *different* one (e.g. learn on WorkBench → apply on
[API-Bank](https://github.com/hgkumbhare/DAMO-ConvAI/tree/main/api-bank)). This is the
**most important axis for the generalization claim**, but it is **not** a clean, fully
independent third factor — it interacts with Axis A.

**Cross-dataset transfer is leakage-proof.** Different tools, entities, templates, and
call format → no shared surface to memorize. If a WorkBench-learned skill lifts API-Bank
accuracy, that is the cleanest possible evidence for C4 and makes S3 irrelevant. Both
benchmarks are already wired (paper Tables 2 & 3), so this is reachable.

**It collapses Axis A toward skills.** An *example* is schema-bound — a WorkBench demo
calls `find_email_address` / `search_tasks`, which do not exist in API-Bank. Episodic
examples cannot cross tool inventories; only **skills** (abstract patterns) transfer. So
of the 2×2×2 cells:
- **Examples × cross-dataset ≈ degenerate** (a WorkBench demo is useless on API-Bank
  until abstracted — at which point it is a skill).
- **Skills × {top-down, bottom-up} × cross-dataset** are the real, powerful cells.

This makes cross-dataset transfer a **direct argument for the skill-library approach**:
skills are the only unit that can cross benchmarks.

**Cleaner framing — a generalization ladder** (increasing strength, decreasing leakage):
```
Rung 1: within-template     (covered templates)              ← current method → LEAKY
Rung 2: within-dataset,     held-out templates/tools         ← weak signal
        (uncovered PM templates)
Rung 3: cross-dataset       (WorkBench → API-Bank)           ← leakage-proof → HEADLINE
```
The measured +24 (covered) vs +3.3 (uncovered) is Rung 1 vs Rung 2. **Rung 3 is the
experiment that makes the paper.**

**Cost / requirements to enable transfer:**
- **Dataset-agnostic skill representation** — triggers match on *semantics*
  ("a param that is an identifier: `*_id`, `*_email`"), never on WorkBench tool names.
- **A thin binding layer** mapping an abstract skill onto the target dataset's tools and
  call format (API-Bank has its own format + an API-search step).

**Verdict:** keep *construction* as the 2×2 (unit × taxonomy source); treat *transfer
scope* as a third, partly-evaluation axis that is the strongest rung of a generalization
ladder and structurally favors skills.

### Skill-card schema (the Q3/Q4 injectable unit)
```
SKILL: identifier-resolution
Trigger:   task names a person/entity, but the tool you need takes an email or id.
Procedure: 1. Call the lookup tool (e.g. find_email_address) to get the identifier.
           2. Pass the EXACT returned value to the next tool.
           3. Never fabricate or guess an id/email.
Rationale: fabricated identifiers are the most common parameter hallucination.
Applies to: any tool whose params include *_email, *_id, assigned_to_*.
[optional held-out micro-demo]:
   find_email_address("Dana Ito") -> ["dana.ito@vertex.example"]
   search_tasks(assigned_to_email="dana.ito@vertex.example")
```
- Contains **no eval entity/template** → leakage-safe by construction.
- **Retrieved by trigger** (situation match: query mentions a name + a tool needs an id),
  not by task similarity — this is the "load the right skill on the fly" mechanism.

---

## 11. Open questions / decisions to make
- Match on query text vs. tool-routing vs. hybrid?
- One shared example block vs. per-tool attachment?
- How large must the bank be before retrieval beats static? (§7.3)
- Do we need a reranker, or is top-k cosine enough at this scale?
- Bank authoring: hand-written, LLM-generated (v2 prompt), or hybrid — and how do we
  audit it for eval overlap?
