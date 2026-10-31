#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
echo '[1/3] BV v0u link capacity scan, adversarial controls and CLI'
python -m pytest -q -p no:cacheprovider tests/test_spk_bv_v0u_link_pressure.py
echo '[2/3] Complete v0t inherited research gate'
bash search/spk_bv_v0t_research_gate.sh
echo '[3/3] Frozen Architecture v1 inherited custody guard'
echo 'SPK BV v0u LINK CAPACITY PRESSURE RESEARCH GATE PASS (independent native scan required)'
