#!/usr/bin/env bash
# Run from an SPK research worktree. This script never edits the repository.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

printf '[1/4] BV v0i evidence/transport contract and adversarial tests\n'
python -m pytest -q tests/test_spk_bv_evidence_cost_v0i.py
printf '[2/4] Independent-process and hashseed-invariant witness\n'
tmp1=$(mktemp); tmp2=$(mktemp)
trap 'rm -f "$tmp1" "$tmp2"' EXIT
PYTHONHASHSEED=1 python -m search.spk_bv_v0i_witness > "$tmp1"
PYTHONHASHSEED=999 python -m search.spk_bv_v0i_witness > "$tmp2"
cmp "$tmp1" "$tmp2"
python - "$tmp1" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    d=json.load(f)
assert d["schema"] == "spk-bv-evidence-transport-cost/v0i"
assert (d["physical_transmissions"],d["distinct_contextual_votes"],
        d["additional_transmissions_over_vote_count"]) == (528,33,495)
assert d["transport_units"]==528 and d["budget_overloads"]
print(json.dumps({k:d[k] for k in (
    "status", "physical_transmissions", "distinct_contextual_votes",
    "additional_transmissions_over_vote_count", "transport_units",
    "physical_sha256", "contextual_vote_sha256")}, sort_keys=True))
PY
printf '[3/4] Frozen Architecture v1 baseline guard (tracked source paths)\n'
if git rev-parse --is-inside-work-tree >/dev/null 2>&1 && \
   git rev-parse -q --verify 'refs/tags/spk-architecture-bounded-reference-v1^{commit}' >/dev/null 2>&1; then
  python - <<'PY'
import subprocess
from pathlib import Path
# Dedicated frozen package trees. This guard is deliberately not advertised
# as replacing the inherited Architecture v1 full release/custody gate.
tag = 'spk-architecture-bounded-reference-v1'
paths = [p for p in ('spk_core', 'spk_network', 'spk_compiler',
                     'spk_simulator', 'spk_architecture')
         if Path(p).is_dir()]
if paths:
    changed = subprocess.check_output(['git','diff','--name-only',tag,'--',*paths], text=True).strip()
    untracked = subprocess.check_output(['git','ls-files','--others','--exclude-standard','--',*paths],text=True).strip()
    if changed or untracked:
        raise SystemExit(f'Frozen-tree delta detected: {changed} {untracked}')
print('Frozen tracked package trees: PASS (run inherited complete guard separately)')
PY
else
  echo 'ARCHITECTURE CUSTODY UNVERIFIED: frozen tag or Git worktree absent'
  exit 2
fi
printf '[4/4] Script is read-only and SPK v0i remains research-only\n'
echo 'SPK BV V0i EVIDENCE/TRANSPORT COST: RESEARCH PASS (no causal credit, learning, or compression)'
