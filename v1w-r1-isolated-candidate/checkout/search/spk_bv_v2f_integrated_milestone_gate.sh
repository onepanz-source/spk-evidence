#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/4] BV v2f integrated source-owned tick batching, receiver feedback, negative boundary'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v2f_integrated_milestone.py
echo '[2/4] v2e native admission experiment + v2d-v2a regressions'
python -m pytest -q --import-mode=importlib \
  tests/test_spk_bv_v2e_native_admission_discrimination.py \
  tests/test_spk_bv_v2d_native_holdout_differential.py \
  tests/test_spk_bv_v2c_temporal_differential.py \
  tests/test_spk_bv_v2b_differential_boundary.py \
  tests/test_spk_bv_v2a_versioned_executor.py
echo '[3/4] Python and shell static syntax'
python -m compileall -q spk_backvalidation_v2/batched_feedback_executor_v2f.py \
  spk_bv_research/vertical_slice_integration_v2f.py \
  search/spk_bv_v2f_integrated_milestone.py
bash -n search/spk_bv_v2f_integrated_milestone_gate.sh
echo '[4/4] BV v2f VERTICAL SLICE GATE PASS: research-native integration remains BLOCKED'
