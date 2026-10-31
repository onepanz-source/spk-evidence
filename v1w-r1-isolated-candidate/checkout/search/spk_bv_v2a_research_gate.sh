#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] v2a owned-event bounded executor conformance, adversarial controls and CLI'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v2a_versioned_executor.py
echo '[2/3] v1z source-bound admission contract (non-native reference boundary)'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1z_native_observer_admission.py
echo '[3/3] Python / shell syntax and frozen-source no-edit policy'
python -m compileall -q spk_backvalidation_v2 spk_bv_research/versioned_executor_admission_v2a.py search/spk_bv_v2a_versioned_executor.py
bash -n search/spk_bv_v2a_research_gate.sh
printf '%s\n' 'BV v2a RESEARCH MICRO EXECUTOR PASS (NOT FULL NATIVE-SPK EQUIVALENCE OR BV LEARNING)'
