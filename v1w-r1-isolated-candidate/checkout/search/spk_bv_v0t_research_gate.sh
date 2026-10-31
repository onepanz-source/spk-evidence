#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
echo '[1/3] New BV v0t three-arm controls, provenance and adversarial tests'
python -m pytest -q -p no:cacheprovider tests/test_spk_bv_v0t_three_arm.py
echo '[2/3] Inherited BV v0r/v0p/v0q semantic correspondence tests'
bash search/spk_bv_v0r_research_gate.sh
echo '[3/3] Frozen Architecture v1 full guard via established inherited gate'
bash search/spk_bv_v0n_research_gate.sh
echo 'SPK BV v0t THREE-ARM RESEARCH GATE: PASS (native triad requires separate command)'
