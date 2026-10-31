#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

echo '[1/4] BV contextual credit evidence adversarial contract'
python -m pytest -q tests/test_spk_bv_contextual_credit_v0a.py

echo '[2/4] BV v0 + frozen Network/A4 selected functional regressions'
python -m pytest -q tests/test_spk_back_validation_contract_v0.py \
  tests/test_network_learning_interface_v0.py \
  tests/test_spk_arch_a4a_operating_modes_v1a.py \
  tests/test_spk_arch_a4c_candidate_promotion_v1c.py

echo '[3/4] Frozen source, ancestry and architecture tag protection'
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo 'ERROR: Git research worktree required for source-custody gate' >&2
  exit 3
fi
base=spk-architecture-bounded-reference-v1
test "$(git rev-parse "$base^{commit}")" = '5af99cd1f4d603bf0c8e1557a6561c107765fdb5'
git merge-base --is-ancestor "$base" HEAD
for root in spk_core spk_network spk_compiler spk_simulator spk_architecture spk_architecture_v1; do
  git diff --quiet "$base" -- "$root"
  git diff --cached --quiet "$base" -- "$root"
  test -z "$(git status --porcelain --untracked-files=all -- "$root")"
done
echo 'Frozen sources unchanged: PASS'

echo '[4/4] Deterministic synthetic negative-control classification'
python - <<'PY'
from pathlib import Path
from spk_backvalidation_v0.contract_v0 import strict_loads
from spk_backvalidation_v0.contextual_credit_v0a import evaluate_credit
x = strict_loads(Path('examples/spk_bv_v0a_synthetic_paired_trials.json').read_text())
r = evaluate_credit(x)
expected = {'beneficial':'EVIDENCE_FOR_FURTHER_VERIFICATION',
            'consensus-trap':'LOCAL_GLOBAL_CONFLICT',
            'ambiguous':'INCONCLUSIVE',
            'global-unavailable':'GLOBAL_UNAVAILABLE',
            'resource-regression':'COST_BLOCKED'}
actual = {row['context_id']:row['decision'] for row in r['context_results']}
assert actual == expected, (actual, expected)
print({'status':r['status'], 'trial_pairs':r['trial_pairs'], 'decisions':actual,
       'evidence_sha256':r['report_sha256']})
PY

echo 'SPK BV CONTEXTUAL CREDIT V0a: RESEARCH STRUCTURAL PASS (not learning, not a release)'
