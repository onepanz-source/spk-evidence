#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1e conditional native receiver readout and adversarial boundaries'
python -m pytest -q tests/test_spk_bv_v1e_receiver_impact.py
python -m compileall -q spk_bv_research/receiver_impact_v1e.py search/spk_bv_v1e_receiver_impact.py
echo '[2/3] Inherited v1d -> Architecture v1 full frozen custody gate'
bash search/spk_bv_v1d_research_gate.sh
echo '[3/3] Native receiver readout requires separate CLI'
echo 'SPK BV v1e CONDITIONAL RECEIVER READOUT RESEARCH PASS (not native feedback or learning)'
