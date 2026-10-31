#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1y external native Python trace parity and trust contract'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1y_native_external_probe.py
python -m compileall -q spk_bv_research/native_external_probe_v1y.py search/spk_bv_v1y_native_external_probe.py
echo '[2/3] Inherited v1x frozen source/observer-reference gate'
bash search/spk_bv_v1x_research_gate.sh
echo '[3/3] External interpreter trace is NOT source-owned native callback'
echo 'SPK BV v1y TRACE RESEARCH GATE PASS (NO NATIVE RECEIVER AUTHORITY)'
