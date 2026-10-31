#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v2g derived native callsite seam / fail closed adversarial contracts'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v2g_derived_native_fork.py
echo '[2/3] Inherited BV v2f native-boundary laboratory and v2e native analysis contracts'
python -m pytest -q --import-mode=importlib \
 tests/test_spk_bv_v2f_integrated_milestone.py \
 tests/test_spk_bv_v2e_native_admission_discrimination.py \
 tests/test_spk_bv_v2d_native_holdout_differential.py \
 tests/test_spk_bv_v2c_temporal_differential.py \
 tests/test_spk_bv_v2b_differential_boundary.py \
 tests/test_spk_bv_v2a_versioned_executor.py
echo '[3/3] BV v2g research gate PASS; native 90-run parity needs explicit CLI'
