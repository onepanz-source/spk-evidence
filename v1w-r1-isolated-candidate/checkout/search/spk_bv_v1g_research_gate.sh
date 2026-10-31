#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1g native original forward/reverse lineage contract and adversarial CLI tests'
python -m pytest -q tests/test_spk_bv_v1g_native_route_lineage.py
python -m compileall -q spk_bv_research/native_route_lineage_v1g.py search/spk_bv_v1g_native_route_lineage.py
echo '[2/3] Inherited v1f + Architecture v1 freeze custody guard'
bash search/spk_bv_v1f_research_gate.sh
echo '[3/3] Original native source-bound route/lineage verification requires separate CLI'
echo 'SPK BV v1g ORIGINAL NATIVE ROUTE LINEAGE RESEARCH PASS (no native variant network replay or learning)'
