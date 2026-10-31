#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] v2e admission discrimination negative/provenance tests'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v2e_native_admission_discrimination.py
echo '[2/3] inherited v2d-v2a regression'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v2d_native_holdout_differential.py tests/test_spk_bv_v2c_temporal_differential.py tests/test_spk_bv_v2b_differential_boundary.py tests/test_spk_bv_v2a_versioned_executor.py
echo '[3/3] code and shell syntax'
python -m compileall -q spk_bv_research/coincident_admission_discrimination_v2e.py search/spk_bv_v2e_native_admission_discrimination.py
bash -n search/spk_bv_v2e_research_gate.sh
printf '%s\n' 'SPK BV v2e NATIVE ADMISSION DISCRIMINATION CONTRACT PASS (NATIVE MATRIX VIA SEPARATE CLI)'
