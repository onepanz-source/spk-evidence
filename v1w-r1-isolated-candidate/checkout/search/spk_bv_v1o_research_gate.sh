#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1o decision disclosure, epistemic authority and adversarial tests'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1o_decision_disclosure.py
python -m compileall -q spk_bv_research/decision_disclosure_boundary_v1o.py search/spk_bv_v1o_decision_disclosure.py
echo '[2/3] Inherited v1n.1 isolated-import hotfix and frozen Architecture v1 custody'
bash search/spk_bv_v1n1_import_hotfix_gate.sh
echo '[3/3] Full native-bound recomputation requires the v1o CLI'
echo 'SPK BV v1o T4 SHADOW DECISION DISCLOSURE RESEARCH PASS (no native authority or learning)'
