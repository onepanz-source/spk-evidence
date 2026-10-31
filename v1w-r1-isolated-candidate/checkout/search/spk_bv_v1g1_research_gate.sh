#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] v1g.1 occurrence/grant temporal semantics and adversarial tests'
python -m pytest -q tests/test_spk_bv_v1g1_occurrence_timing_hotfix.py tests/test_spk_bv_v1g_native_route_lineage.py
python -m compileall -q spk_bv_research/native_route_lineage_v1g.py search/spk_bv_v1g_native_route_lineage.py
echo '[2/3] Inherited v1g regression chain and frozen Architecture v1 custody'
bash search/spk_bv_v1g_research_gate.sh
echo '[3/3] Source-bound original native occurrence/grant join requires separate CLI'
echo 'SPK BV v1g.1 TEMPORAL OCCURRENCE/GRANT HOTFIX: RESEARCH PASS (native run separate)'
