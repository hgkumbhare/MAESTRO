#!/bin/bash
# Wait until PM+analytics finish (base+All) for both 70B/72B models, then launch
# the remaining datasets. Price-sorted routing (config default).
cd /Users/harshadakumbhare/Documents/GitHub/research_project/MAESTRO_v2
PY=/opt/anaconda3/envs/maestro2/bin/python
REST="calendar customer_relationship_manager email multi_domain"

check() {
  "$PY" - <<'PYEOF'
import json, os, sys
def ok(model, ds):
    m = f"experiments/E12_abalation/by_model/{model}/{ds}/results/metrics.json"
    if not os.path.exists(m):
        return False
    recs = {r["condition"] for r in json.load(open(m))["records"]}
    return "base" in recs and "skills_gated_verify_with_tool_dependency_skills" in recs
done = (ok("llama3.3-70b", "analytics")
        and ok("qwen-2.5-72b", "project_management")
        and ok("qwen-2.5-72b", "analytics"))
sys.exit(0 if done else 1)
PYEOF
}

echo "waiting for PM+analytics (both models) to complete..."
until check; do sleep 60; done
echo "PM+analytics complete: launching remaining datasets"
"$PY" experiments/E12_abalation/run_llama70b_base_all.py $REST > experiments/E12_abalation/results/llama70b_rest.log 2>&1 &
"$PY" experiments/E12_abalation/run_qwen72b_base_all.py $REST > experiments/E12_abalation/results/qwen72b_rest.log 2>&1 &
echo "launched remaining datasets for both models"
