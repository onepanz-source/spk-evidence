#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1f receiver preference polarity, safety and adversarial tests'
python -m pytest -q tests/test_spk_bv_v1f_receiver_preference.py
python -m compileall -q spk_bv_research/receiver_preference_v1f.py search/spk_bv_v1f_receiver_preference.py
echo '[2/3] Inherited v1e -> Architecture v1 frozen custody guard'
bash search/spk_bv_v1e_research_gate.sh
echo '[3/3] Native source-bound v1f recomputation requires separate CLI'
echo 'SPK BV v1f DECLARED RECEIVER PREFERENCE POLARITY RESEARCH PASS (not native judgment or learning)'
