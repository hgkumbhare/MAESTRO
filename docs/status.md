# Project Status — snapshot

> 📄 **Findings writeup (grow into the paper): [writeup.md](./writeup.md)** — headline result E1.7:
> gated skills **+11.2 real-task accuracy / −5.6 side effects** on the team-comparable improved-tools base.


A single-page snapshot of where the MAESTRO tool-hallucination work stands. Living doc;
update as experiments land. Deeper docs linked inline.

## The story so far
1. **Diagnosed the current method.** The paper's "improved" = integration-test *source
   text* stapled into tool descriptions (no runtime validation). See
   [workbench_and_integration_tests.md](./workbench_and_integration_tests.md).
2. **Found leakage (measured).** The integration tests reproduce 5 of 8 PM eval templates
   (+ real entities). Result: `improved` gain is +24 on covered templates vs +3.3 (noise)
   on uncovered → **memorization, not generalization** ([paper_review.md](./paper_review.md) S3).
3. **Reframed the contribution** as a leakage-safe, scalable, dataset-agnostic
   **tool-interaction skill library** (retrieved on the fly), tested for **generalization**
   (held-out domains) and ultimately **cross-dataset** transfer (WorkBench→API-Bank).
   Design + 2×2×2 space (unit × taxonomy-source × transfer-scope):
   [retrieval_design.md](./retrieval_design.md).
4. **Built the experiment infra** — `experiments/` with shared `common/` (skill cards,
   leakage audit gate, scoring, conditions, sandbox, pricing, config-driven runner) and
   one folder per experiment (README + RESULTS + config + results). Reporting standard:
   [reporting_standard.md](./reporting_standard.md). Roadmap:
   [experiment_plan.md](./experiment_plan.md).

## Latest result — E1 PM pilot (base vs skills, 80 PM queries, gpt-4o-mini)
| condition | split | n | acc % | Δ base | side-eff % |
|---|---|---|---|---|---|
| base | covered | 50 | 36.0 | — | 0.0 |
| base | uncovered | 30 | 40.0 | — | 6.7 |
| skills | covered | 50 | 44.0 | +8.0 | 0.0 |
| skills | uncovered | 30 | 43.3 | +3.3 | 0.0 |

**Read:** skills give a *balanced* lift (covered +8 ≈ uncovered +3.3) — **no leakage
signature** (unlike improved's 7× covered spike), plus side-effects 6.7%→0%. But magnitude
is small and PM's 30 uncovered = within noise. **Inconclusive on PM alone → the all-domains
run (untouched domains) is the decisive test.** Note: covered/uncovered is only a *leakage
guardrail* for skills (they apply to both equally); the real skills metric is per-domain
held-out.

## E1 COMPLETE — base vs skills, all domains (smolagents, temp 0, 690×2)
| | overall | calendar | PM | email | multi | analytics | CRM |
|---|---|---|---|---|---|---|---|
| base % | 44.9 | 71.8 | 38.8 | 48.9 | 35.7 | 40.0 | 41.2 |
| skills % | 47.4 | 84.5 | 45.0 | 52.2 | 36.2 | 37.5 | 37.5 |
| Δ acc | **+2.5** | +12.7 | +6.2 | +3.3 | +0.5 | −2.5 | −3.7 |

**Verdict:** small, MIXED win — helps calendar/PM/email, hurts CRM/analytics. Side-effects
net flat (~40%). Top-down hand-written skills are inconsistent (likely don't fit smolagents'
code-agent paradigm). C1 resolved (all domains score non-zero). Full: E1 RESULTS.md.

## Where we are on the roadmap
- **E0** ✅ leakage diagnostic. **E1** ✅ complete (above). C1 ✅ resolved.
- **Next:** E2 (ground skills w/ held-out demos) or E8 (bottom-up derivation) — E1 shows
  generic top-down skills aren't enough; diagnose CRM/analytics regressions.
- E3–E7 scaffolded, not run.

## Cost so far
~$10 total OpenAI spend to date (`python scripts/check_openai_spend.py`), most of it
unrelated; experiments have cost well under $1 combined.

## Next action
Run the entire dataset (all domains) with checkpointing, then fill E1 Table A (PM) +
Table B (untouched domains).
