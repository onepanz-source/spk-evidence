#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] v2c bounded causal-time scheduler source-owned observations, provenance and adversarial CLI'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v2c_temporal_differential.py
echo '[2/3] Inherited v2b finite differential and v2a executable source contract'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v2b_differential_boundary.py tests/test_spk_bv_v2a_versioned_executor.py
echo '[3/3] v2c syntax, shell, and isolated source guard'
python -m compileall -q spk_backvalidation_v2/time_order_executor_v2c.py spk_bv_research/temporal_differential_v2c.py search/spk_bv_v2c_temporal_differential.py
bash -n search/spk_bv_v2c_research_gate.sh
printf '%s\n' 'SPK BV v2c FINITE MICRO TIME-ORDER RESEARCH PASS (NOT SPK SCHEDULER OR CMP EQUIVALENCE)'
