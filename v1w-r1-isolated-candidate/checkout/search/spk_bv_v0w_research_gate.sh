#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
echo '[1/2] BV v0w workload shifts/repetitions, provenance and CLI negative tests'
python -m pytest -q -p no:cacheprovider tests/test_spk_bv_v0w_workload_sensitivity.py
echo '[2/2] Inherited BV v0v gate incl. Architecture v1 custody guard'
bash search/spk_bv_v0v_research_gate.sh
echo 'SPK BV v0w TEMPORAL WORKLOAD RESEARCH GATE PASS (native CLI separate)'
