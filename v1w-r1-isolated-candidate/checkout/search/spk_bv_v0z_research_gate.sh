#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
echo '[1/2] BV v0z hypothetical update eligibility and adversarial tests'
python -m pytest -q -p no:cacheprovider tests/test_spk_bv_v0z_shadow_update.py
echo '[2/2] Inherited BV v0y and earlier research regression gates'
bash search/spk_bv_v0y_research_gate.sh
echo 'SPK BV v0z SHADOW UPDATE RESEARCH PASS (no native update or learning)'
