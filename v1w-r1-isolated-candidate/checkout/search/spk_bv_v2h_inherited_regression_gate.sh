#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/2] BV v2g/v2f/v2e inherited conformance and differential research tests'
python -m pytest -q --import-mode=importlib \
  tests/test_spk_bv_v2g_derived_native_fork.py \
  tests/test_spk_bv_v2f_integrated_milestone.py \
  tests/test_spk_bv_v2e_native_admission_discrimination.py \
  tests/test_spk_bv_v2d_native_holdout_differential.py \
  tests/test_spk_bv_v2c_temporal_differential.py \
  tests/test_spk_bv_v2b_differential_boundary.py \
  tests/test_spk_bv_v2a_versioned_executor.py
echo '[2/2] BV v2h inherited selected regressions PASS'
