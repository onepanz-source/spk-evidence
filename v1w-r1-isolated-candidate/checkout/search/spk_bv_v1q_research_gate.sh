#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1q full-factorial interaction contract, independent fixtures and adversarial CLI'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1q_native_factorial_interactions.py
python -m compileall -q spk_bv_research/native_factorial_interaction_v1q.py search/spk_bv_v1q_native_factorial_interactions.py
echo '[2/3] Inherited v1p native source custody and Architecture v1 freeze gate'
bash search/spk_bv_v1p_research_gate.sh
echo '[3/3] Frozen native 16-arm factorial matrix requires separate CLI'
echo 'SPK BV v1q FULL FACTORIAL RESEARCH PASS (counts, not feedback credit or learning)'
