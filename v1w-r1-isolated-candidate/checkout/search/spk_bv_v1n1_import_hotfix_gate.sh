#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1n.1 isolated pytest import/fixture regression'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1n_receiver_knowledge_disclosure.py
python -m compileall -q tests/test_spk_bv_v1n_receiver_knowledge_disclosure.py
echo '[2/3] BV v1m inherited synthetic fixture regression (isolated test import)'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1m_native_passive_projection.py
echo '[3/3] Inherited BV v1n gate and frozen Architecture v1 custody checks'
bash search/spk_bv_v1n_research_gate.sh
echo 'SPK BV v1n.1 TEST IMPORT HOTFIX: RESEARCH PASS (native evidence separate)'
