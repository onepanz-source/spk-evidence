#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
repo=$(cd "$(dirname "$0")/.." && pwd -P)
cd "$repo"
echo '[1/4] Simulator-backed paired execution and adversarial replay'
python -m pytest -q tests/test_spk_bv_simulator_evidence_v0b.py
printf '\n[2/4] Inherited BV contracts and selected frozen functional regressions\n'
python -m pytest -q \
  tests/test_spk_back_validation_contract_v0.py \
  tests/test_spk_bv_contextual_credit_v0a.py \
  tests/test_network_learning_interface_v0.py \
  tests/test_spk_arch_a4a_operating_modes_v1a.py \
  tests/test_spk_arch_a4c_candidate_promotion_v1c.py 
printf '\n[3/4] Frozen reference integrity and branch ancestry\n'
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  tag=spk-architecture-bounded-reference-v1
  test "$(git rev-parse "${tag}^{commit}")" = "5af99cd1f4d603bf0c8e1557a6561c107765fdb5"
  git merge-base --is-ancestor "$tag" HEAD
  for dir in spk_core spk_network spk_compiler spk_simulator spk_architecture spk_architecture_v1; do
    git diff --quiet "$tag" -- "$dir"
    git diff --cached --quiet "$tag" -- "$dir"
    test -z "$(git ls-files --others --exclude-standard -- "$dir")"
  done
  echo 'Frozen referenced modules unchanged: PASS'
else
  echo 'ERROR: Git research worktree is required for frozen reference checks' >&2
  exit 3
fi
printf '\n[4/4] Generate evidence and verify independent rerun\n'
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
python -m search.spk_bv_v0b_simulator_evidence --write "$tmp"
python -m search.spk_bv_v0b_simulator_evidence --verify "$tmp"
echo 'SPK BV V0b SIMULATOR-BACKED PAIRED EVIDENCE: RESEARCH PASS (offline, not learning)'
