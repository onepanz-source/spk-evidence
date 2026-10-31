#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1r rational allocation, source lineage, polarity and adversarial CLI'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1r_allocation_boundary.py
python -m compileall -q spk_bv_research/native_allocation_boundary_v1r.py search/spk_bv_v1r_allocation_boundary.py
echo '[2/3] Inherited v1q -> frozen Architecture v1 custody gate'
bash search/spk_bv_v1q_research_gate.sh
echo '[3/3] Native source-bound v1q recomputation requires separate CLI'
echo 'SPK BV v1r RATIONAL FACTORIAL ACCOUNTING PASS (no utility, receiver credit or learning)'
