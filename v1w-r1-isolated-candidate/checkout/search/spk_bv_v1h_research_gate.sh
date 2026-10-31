#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1h bounded full-native-network counterfactual and adversarial contract tests'
python -m pytest -q tests/test_spk_bv_v1h_native_network_counterfactual.py
python -m compileall -q spk_bv_research/native_network_counterfactual_v1h.py search/spk_bv_v1h_network_counterfactual.py
echo '[2/3] Inherited v1g.1 full source-bound route/lineage research and Architecture v1 custody'
bash search/spk_bv_v1g1_research_gate.sh
echo '[3/3] Native whole-network A-variant scheduler replay requires separate fwork CLI'
echo 'SPK BV v1h NETWORK COUNTERFACTUAL RESEARCH PASS (no native result until CLI, no learning)'
