#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

echo '[1/4] New read-only Back Validation Contract v0 conformance tests'
python -m pytest -q tests/test_spk_back_validation_contract_v0.py

echo '[2/4] Baseline Network v0 observer and A4 authority regression'
python -m pytest -q \
  tests/test_network_learning_interface_v0.py \
  tests/test_spk_arch_a4a_operating_modes_v1a.py \
  tests/test_spk_arch_a4c_candidate_promotion_v1c.py

echo '[3/4] Frozen source protection (if in a Git worktree)'
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  baseline=spk-architecture-bounded-reference-v1
  git rev-parse -q --verify "refs/tags/$baseline" >/dev/null
  git merge-base --is-ancestor "$baseline" HEAD
  for root in spk_core spk_network spk_compiler spk_simulator spk_architecture spk_architecture_v1; do
    git diff --quiet "$baseline" -- "$root"
    git diff --cached --quiet "$baseline" -- "$root"
  done
  echo 'Frozen SPK sources unchanged relative to Architecture v1 tag: PASS'
else
  echo 'Not a Git worktree: source protection requires fwork Git gate'
fi

echo '[4/4] JSON conformance witness'
python - <<'PY'
from pathlib import Path
from spk_backvalidation_v0.contract_v0 import strict_loads, validate_trace
p = Path('examples/spk_bv_v0_distributed_feedback.json')
print(validate_trace(strict_loads(p.read_text())))
PY

echo 'SPK BACK VALIDATION CONTRACT v0: RESEARCH CONFORMANCE PASS (offline structural domain)'
