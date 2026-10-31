#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1c isolated native operand-sensitivity model and negative controls'
python -m pytest -q tests/test_spk_bv_v1c_native_sensitivity.py
python -m compileall -q spk_bv_research/native_sensitivity_v1c.py search/spk_bv_v1c_native_sensitivity.py
echo '[2/3] Inherited BV v1b.1 gate and frozen Architecture v1 guard'
bash search/spk_bv_v1b1_hotfix_gate.sh
echo '[3/3] Source-bound native sensitivity requires separate CLI'
echo 'SPK BV v1c ISOLATED NATIVE OPERATOR SENSITIVITY: RESEARCH PASS (native probe separate)'
