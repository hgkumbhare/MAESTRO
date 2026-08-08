"""Leakage audit gate — check_example(candidate) -> {leaks, reasons}.

Enforces disjointness between a candidate example/skill-demo and the eval set on the
axes from docs/retrieval_design.md §6.3:
  1. entity   (exact)     — no eval name/email/id appears in the candidate
  2. template (normalized)— candidate task, entities masked, != any eval base_template
  3. semantic (embedding) — OPTIONAL; max cosine sim to eval queries below threshold
  4. answer   (exact)     — candidate tool-call chain != any eval ground-truth  (caller-supplied)

This is the reusable brick for E3 (example bank) and the retrieval-time guard (E4).
Semantic check is optional and lazily imports sentence-transformers so E0–E2 don't need it.
"""
import ast
import glob
import os
import re

import pandas as pd

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ID_RE = re.compile(r"\b\d{8}\b")


def build_reference(data_dir: str = "data/processed") -> dict:
    """Extract the eval reference sets: entity blocklist + templates + queries."""
    entities = set()
    templates = set()
    queries = []

    # Entities from all processed CSVs (emails + 8-digit ids across all cells).
    for csv in glob.glob(os.path.join(data_dir, "*.csv")):
        try:
            text = pd.read_csv(csv, dtype=str).to_csv(index=False)
        except Exception:
            continue
        entities.update(EMAIL_RE.findall(text))
        entities.update(ID_RE.findall(text))

    # Templates + queries from the queries-and-answers CSVs.
    qa_dir = os.path.join(data_dir, "queries_and_answers")
    for csv in glob.glob(os.path.join(qa_dir, "*.csv")):
        df = pd.read_csv(csv, dtype=str)
        if "base_template" in df.columns:
            templates.update(df["base_template"].dropna().str.strip().tolist())
        if "query" in df.columns:
            queries.extend(df["query"].dropna().tolist())
        # entities also live in the answer strings
        if "answer" in df.columns:
            joined = " ".join(df["answer"].dropna().tolist())
            entities.update(EMAIL_RE.findall(joined))
            entities.update(ID_RE.findall(joined))

    return {"entities": entities, "templates": templates, "queries": queries}


def _template_to_regex(template: str):
    """Turn an eval base_template into a matcher by replacing {placeholders} with wildcards.

    e.g. "Move all of {name}'s tasks that are in progress to in review"
         -> matches "Move all of Priya Nair's tasks that are in progress to in review"
    """
    esc = re.escape(template.strip())
    # re.escape renders "{name}" as "\{name\}"; swap each placeholder for a non-greedy wildcard.
    pattern = re.sub(r"\\\{.*?\\\}", r".+?", esc)
    return re.compile(pattern, re.IGNORECASE)


def _template_matchers(templates):
    matchers = []
    for t in templates:
        if not t or "{" not in t:
            continue  # only placeholdered templates are useful as matchers
        try:
            matchers.append((t, _template_to_regex(t)))
        except re.error:
            continue
    return matchers


def check_example(candidate: dict, reference: dict, use_semantic: bool = False,
                  sim_threshold: float = 0.8) -> dict:
    """Return {'leaks': bool, 'reasons': [...]}.

    candidate: {'task': str, 'text': str (optional full demo), 'answer': [calls] (optional)}
    reference: output of build_reference().
    """
    reasons = []
    task = candidate.get("task", "")
    blob = candidate.get("text", "") + " " + task

    # 1. Entity check (exact substring on emails/ids).
    for ent in reference["entities"]:
        if ent and ent in blob:
            reasons.append(f"entity-overlap:{ent}")
            break

    # 2. Template check (regex from each placeholdered eval template).
    for tmpl, matcher in _template_matchers(reference["templates"]):
        if matcher.search(task):
            reasons.append(f"template-overlap:{tmpl}")
            break

    # 4. Answer/outcome check (exact chain match), if provided.
    ans = candidate.get("answer")
    if ans:
        cand_chain = tuple(sorted(str(a).strip().lower() for a in ans))
        # Caller may pass reference answers; skipped here unless provided.
        for gt in reference.get("answers", []):
            if tuple(sorted(str(a).strip().lower() for a in gt)) == cand_chain:
                reasons.append("answer-overlap")
                break

    # 3. Semantic check (optional; lazy import).
    if use_semantic:
        try:
            from sentence_transformers import SentenceTransformer, util  # lazy
            model = _get_embedder()
            q_emb = model.encode(task, convert_to_tensor=True)
            ref_emb = model.encode(reference["queries"], convert_to_tensor=True)
            max_sim = float(util.cos_sim(q_emb, ref_emb).max())
            if max_sim >= sim_threshold:
                reasons.append(f"semantic-overlap:{max_sim:.2f}")
        except Exception as e:  # pragma: no cover
            reasons.append(f"semantic-check-skipped:{e}")

    return {"leaks": len(reasons) > 0, "reasons": reasons}


_EMBEDDER = None


def _get_embedder():
    global _EMBEDDER
    if _EMBEDDER is None:
        from sentence_transformers import SentenceTransformer
        _EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBEDDER
