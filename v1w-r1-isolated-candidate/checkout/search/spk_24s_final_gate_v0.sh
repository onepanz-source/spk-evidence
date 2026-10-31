#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Independent 168 causal triplets / 504 conditions\n'
python -m pytest -q tests/test_spk_24s_budget_triads_v0.py

printf '\n[2/6] Frozen Network causal isolation and passive-observer invariance\n'
python -m pytest -q tests/test_spk_24s_frozen_causal_failure_v0.py

printf '\n[3/6] Canonical receipts and complete replay across separate Python processes\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_24s_causal_failure_evidence_v0 --write "$tmp/a.json"
python -m search.spk_24s_causal_failure_evidence_v0 --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_24s_causal_failure_evidence_v0 --verify "$tmp/a.json"
python -m search.spk_24s_causal_failure_evidence_v0 --verify "$tmp/b.json"

printf '\n[4/6] 24q and 24r failure-contract regression\n'
python -m pytest -q \
    tests/test_spk_24q_limit_probe_plan_v0.py \
    tests/test_spk_24q_frozen_failure_parity_v0.py \
    tests/test_spk_24r_dual_limit_plan_v0.py \
    tests/test_spk_24r_frozen_dual_limit_v0.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen-source boundary and patch hygiene\n'
git diff --check
if [[ -n "$(git diff --name-only HEAD -- spk_core spk_network spk_compiler spk_architecture spk_simulator)" ]]; then
  echo 'FAIL: frozen/prior simulator modifications' >&2
  exit 1
fi
if [[ -n "$(git diff --cached --name-only)" ]]; then
  echo 'FAIL: unexpected staged changes' >&2
  exit 1
fi
python - <<'PY'
from pathlib import Path
names = (
    'docs/spk-24s-causal-budget-isolation-v0.md',
    'search/spk_24s_budget_triads_v0.py',
    'search/spk_24s_causal_failure_evidence_v0.py',
    'search/spk_24s_final_gate_v0.sh',
    'tests/test_spk_24s_budget_triads_v0.py',
    'tests/test_spk_24s_frozen_causal_failure_v0.py',
)
for name in names:
    data = Path(name).read_bytes()
    if (b'\r' in data or not data.endswith(b'\n') or
            any(line.endswith((b' ', b'\t')) for line in data.splitlines())):
        raise SystemExit('24s whitespace failure: ' + name)
print('24s structure/whitespace: PASS')
PY
git status --short
printf '\nSPK 24s CAUSAL BUDGET ISOLATION GATE: PASS (bounded diagnostic scope)\n'
