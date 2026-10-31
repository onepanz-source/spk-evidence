#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1n finite knowledge disclosure, provenance and adversarial contract'
python -m pytest -q tests/test_spk_bv_v1n_receiver_knowledge_disclosure.py
python -m compileall -q spk_bv_research/receiver_knowledge_disclosure_v1n.py search/spk_bv_v1n_knowledge_disclosure.py
echo '[2/3] Inherited v1m native source and frozen Architecture v1 custody'
bash search/spk_bv_v1m_research_gate.sh
echo '[3/3] Full native v1m predecessor replay and v1n attestations require separate CLI'
echo 'SPK BV v1n RESEARCH CONTRACT PASS (no native disclosure, judgment or learning)'
