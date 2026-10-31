#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] v2b native-source differential projection, causal counterexample and adversarial CLI'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v2b_differential_boundary.py
echo '[2/3] Inherited v2a source-owned experimental scheduler conformance'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v2a_versioned_executor.py
echo '[3/3] Syntax, source policy; native attestation is separate'
python -m compileall -q spk_bv_research/native_micro_differential_v2b.py search/spk_bv_v2b_differential_boundary.py
bash -n search/spk_bv_v2b_research_gate.sh
printf '%s\n' 'SPK BV v2b FINITE COUNT ALIGNMENT + TEMPORAL COUNTEREXAMPLE RESEARCH PASS (NO NATIVE SEMANTIC EQUIVALENCE)'
