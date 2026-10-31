#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
echo '[1/2] BV v0x cost-to-utility non-identifiability, negative controls and CLI'
python -m pytest -q -p no:cacheprovider tests/test_spk_bv_v0x_value_boundary.py
echo '[2/2] Inherited BV v0w gate and Architecture v1 custody guard'
bash search/spk_bv_v0w_research_gate.sh
echo 'SPK BV v0x VALUE BOUNDARY RESEARCH PASS (native reexecution requires separate command)'
