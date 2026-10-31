#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1z versioned source-owned observer admission contract and adverse boundaries'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1z_native_observer_admission.py
python -m compileall -q spk_bv_research/native_observer_v2_boundary_v1z.py search/spk_bv_v1z_native_observer_admission.py
 echo '[2/3] Inherited frozen-source custody / v1y.1 research gate'
if [[ -f search/spk_bv_v1y1_native_hash_parity_hotfix_gate.sh ]]; then
  bash search/spk_bv_v1y1_native_hash_parity_hotfix_gate.sh
else
  bash search/spk_bv_v1y_research_gate.sh
fi
echo '[3/3] Native v2 instrumented scheduler is absent: explicit BLOCKED gate'
echo 'SPK BV v1z VERSIONED NATIVE OBSERVER ADMISSION CONTRACT PASS (NO NATIVE V2 INSTALLATION)'
