#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
echo '[1/2] BV v0y strict shadow judgment temporal/causal guards and CLI'
python -m pytest -q -p no:cacheprovider tests/test_spk_bv_v0y_judgment_contract.py
echo '[2/2] Inherited BV v0x native-cost boundary and prior research regressions'
bash search/spk_bv_v0x_research_gate.sh
echo 'SPK BV v0y JUDGMENT CONTRACT RESEARCH PASS (no native judgment and no learning)'
