#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
echo '[1/2] BV v0v link/inflight factorial: local invariants, anchors and CLI adversarial tests'
python -m pytest -q -p no:cacheprovider tests/test_spk_bv_v0v_inflight_pressure.py
echo '[2/2] Inherited BV v0u research gate and frozen Architecture v1 custody guard'
bash search/spk_bv_v0u_research_gate.sh
echo 'SPK BV v0v LINK/INFLIGHT RESEARCH GATE PASS (independent native 18-run scan required)'
