#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1p source-bound native exogenous intervention matrix and adversarial controls'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1p_native_causal_locus.py
python -m compileall -q spk_bv_research/native_causal_locus_v1p.py search/spk_bv_v1p_native_causal_locus.py
echo '[2/3] Inherited v1o and Architecture v1 frozen custody gate'
bash search/spk_bv_v1o_research_gate.sh
echo '[3/3] Source-bound 8-arm native intervention matrix requires separate CLI'
echo 'SPK BV v1p NATIVE CAUSAL LOCUS RESEARCH PASS (no endogenous judgment or learning)'
