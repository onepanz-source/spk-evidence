#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v2d explicit-tick and native historical holdout differential adversarial tests'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v2d_native_holdout_differential.py
echo '[2/3] Inherited v2c/v2b/v2a bounded executor regressions'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v2c_temporal_differential.py tests/test_spk_bv_v2b_differential_boundary.py tests/test_spk_bv_v2a_versioned_executor.py
echo '[3/3] Python and shell syntax'
python -m compileall -q spk_backvalidation_v2/explicit_input_executor_v2d.py spk_bv_research/native_holdout_differential_v2d.py search/spk_bv_v2d_native_holdout_differential.py
bash -n search/spk_bv_v2d_research_gate.sh
printf '%s\n' 'SPK BV v2d PREEXISTING NATIVE COINCIDENT WORKLOAD COUNT CONTRAST PASS (NO CMP EQUIVALENCE)'
