"""
S3 leakage experiment: does the integration-test 'improved' gain concentrate on the
5 PM templates that HAVE a matching integration test (covered), or does it also lift
the 3 templates with NO test (uncovered)?

  covered-only gain  -> template/procedure leakage / memorization
  uncovered gain too -> genuine generalization

Runs gpt-4o-mini on the 80 PM queries under two conditions (base vs improved+tests),
scores each query with the repo's own is_correct(), and splits accuracy by template
coverage. Writes per-query CSVs to the scratchpad for inspection.
"""
import os, sys, ast
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.curdir)
sys.path.append(PROJECT_ROOT)

from freezegun import freeze_time
freeze_time("2023-11-30")

from src.evals.utils import generate_results, is_correct

QUERIES = "data/processed/queries_and_answers/project_management_queries_and_answers.csv"
MODEL = "gpt-4o-mini-2024-07-18"
OUT_DIR = "/private/tmp/claude-501/-Users-Documents-hgk-MAESTRO-main/3578f8a8-c0b2-4578-bdc5-94c84b31d764/scratchpad"

# Templates that HAVE an integration test (substring match on base_template).
COVERED_KEYS = [
    "in progress to in review",
    "overdue tasks in the backlog to in progress",
    "in review to completed",
    "sick so reassign",
    "unfinished tasks to the backlog",
]


def coverage(base_template):
    t = str(base_template).lower()
    return "covered" if any(k in t for k in COVERED_KEYS) else "uncovered"


def score_condition(label, tool_set, include_integration_tests):
    print(f"\n===== RUN: {label} (tool_set={tool_set}, tests={include_integration_tests}) =====")
    gt = pd.read_csv(QUERIES)
    gt["answer"] = gt["answer"].apply(ast.literal_eval)

    preds = generate_results(
        QUERIES, MODEL,
        tool_selection="all",
        agent_engine="langchain",
        tool_set=tool_set,
        include_integration_tests=include_integration_tests,
    )
    preds = preds.rename(columns={"function_calls": "prediction"}).fillna("")
    df = preds.merge(gt.rename(columns={"answer": "ground_truth"}), on="query")

    df["prediction"] = df["prediction"].apply(lambda a: [x.replace("\n", "\\n") for x in a])
    df["ground_truth"] = df["ground_truth"].apply(lambda a: [x.replace("\n", "\\n") for x in a])
    df["correct"] = [is_correct(p, g, e) for p, g, e in zip(df["prediction"], df["ground_truth"], df["error"])]
    df["coverage"] = df["base_template"].apply(coverage)
    df["condition"] = label

    df.to_csv(os.path.join(OUT_DIR, f"leakage_{label}.csv"), index=False)
    return df


def summarize(base_df, imp_df):
    print("\n\n########## RESULTS: covered vs uncovered ##########")
    rows = []
    for cov in ["covered", "uncovered", "all"]:
        def acc(d):
            sub = d if cov == "all" else d[d["coverage"] == cov]
            return 100.0 * sub["correct"].mean(), len(sub)
        b_acc, b_n = acc(base_df)
        i_acc, i_n = acc(imp_df)
        rows.append((cov, b_n, b_acc, i_acc, i_acc - b_acc))
    print(f"{'group':<10} {'n':>4} {'base%':>8} {'improved%':>10} {'delta':>8}")
    for cov, n, b, i, d in rows:
        print(f"{cov:<10} {n:>4} {b:>8.1f} {i:>10.1f} {d:>+8.1f}")
    print("\nInterpretation:")
    print("  covered delta >> uncovered delta  ->  leakage / memorization (S3)")
    print("  uncovered delta ~ covered delta   ->  genuine generalization (C4)")


if __name__ == "__main__":
    base_df = score_condition("base", tool_set="original", include_integration_tests=False)
    imp_df = score_condition("improved", tool_set="improved", include_integration_tests=True)
    summarize(base_df, imp_df)
