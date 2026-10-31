#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1x versioned reference observation-port and native baseline custody tests'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1x_reference_observation_port.py
python -m compileall -q spk_bv_research/reference_observation_port_v1x.py search/spk_bv_v1x_reference_observation_port.py
echo '[2/3] Inherited v1w full frozen custody gate'
bash search/spk_bv_v1w_research_gate.sh
echo '[3/3] No native hook installed; reference-only event source and frozen no-observer baseline'
echo 'SPK BV v1x REFERENCE OBSERVER PORT GATE PASS (NOT NATIVE LIVE BV)'
