#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

printf '[1/4] BV v0g causal-closure, convergent/recursive stress and adversarial traces\n'
python -m pytest -q tests/test_spk_bv_causal_audit_v0g.py

printf '[2/4] Inherited BV v0-v0f and frozen observer/authority functional regressions\n'
python -m pytest -q \
  tests/test_spk_bv_n_node_scheduler_v0f.py \
  tests/test_spk_bv_live_dual_scheduler_v0e.py \
  tests/test_spk_bv_a3d_shared_grants_v0d.py \
  tests/test_spk_bv_feedback_transport_v0c.py \
  tests/test_spk_bv_simulator_evidence_v0b.py \
  tests/test_spk_bv_contextual_credit_v0a.py \
  tests/test_spk_back_validation_contract_v0.py \
  tests/test_network_learning_interface_v0.py \
  tests/test_spk_arch_a4c_candidate_promotion_v1c.py

printf '[3/4] Frozen source custody and Architecture v1 ancestry\n'
ref=spk-architecture-bounded-reference-v1
expected=5af99cd1f4d603bf0c8e1557a6561c107765fdb5
[[ "$(git branch --show-current)" == 'spk-backvalidation-v0' ]]
[[ "$(git rev-parse "$ref^{commit}")" == "$expected" ]]
git merge-base --is-ancestor "$expected" HEAD
if ! git diff --quiet "$ref" -- spk spk_core spk_network spk_compiler spk_simulator spk_architecture spk_architecture_v1; then
  echo 'FAIL: frozen modules mutated' >&2; exit 1
fi
if [[ -n "$(git ls-files --others --exclude-standard -- spk spk_core spk_network spk_compiler spk_simulator spk_architecture spk_architecture_v1)" ]]; then
  echo 'FAIL: untracked file in frozen modules' >&2; exit 1
fi
printf 'Frozen source custody and ancestry: PASS\n'

printf '[4/4] Independent-process replay, convergent cost and explicit ambiguity boundary\n'
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
python -m search.spk_bv_v0g_causal_stress_evidence --write "$tmp"
python -m search.spk_bv_v0g_causal_stress_evidence --verify "$tmp"
printf 'SPK BV V0g CAUSAL CLOSURE / CONVERGENCE STRESS: RESEARCH PASS (read-only checker, no causal-credit proof or learning)\n'
