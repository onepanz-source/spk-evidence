#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '[1/4] A3d-anchored shared-credit bridge: functional, contention and adversarial tests\n'
python -m pytest -q tests/test_spk_bv_a3d_shared_grants_v0d.py

printf '[2/4] Inherited BV v0/v0a/v0b/v0c and frozen observer/authority tests\n'
python -m pytest -q \
  tests/test_spk_bv_feedback_transport_v0c.py \
  tests/test_spk_back_validation_contract_v0.py \
  tests/test_spk_bv_contextual_credit_v0a.py \
  tests/test_spk_bv_simulator_evidence_v0b.py \
  tests/test_network_learning_interface_v0.py \
  tests/test_spk_arch_a4c_candidate_promotion_v1c.py

printf '[3/4] Frozen Git ancestry and source guard\n'
ref=spk-architecture-bounded-reference-v1
expected=5af99cd1f4d603bf0c8e1557a6561c107765fdb5
[[ "$(git rev-parse "$ref^{commit}")" = "$expected" ]]
git merge-base --is-ancestor "$expected" HEAD
if ! git diff --quiet "$ref" -- spk spk_core spk_network spk_compiler spk_simulator spk_architecture spk_architecture_v1; then
  echo 'FAIL: frozen SPK source modified' >&2
  exit 1
fi
printf 'Frozen source guard: PASS\n'

printf '[4/4] A3d independent-process source/grant replay with BV contention\n'
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
python -m search.spk_bv_v0d_shared_evidence --write "$tmp"
python -m search.spk_bv_v0d_shared_evidence --verify "$tmp"
printf 'SPK BV V0d A3d SHARED-GRANT OVERLAY: RESEARCH PASS (forward-priority, NOT live scheduler)\n'
