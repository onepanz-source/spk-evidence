#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1d preregistered synthetic objective, native readout guards, holdout controls'
python -m pytest -q tests/test_spk_bv_v1d_native_criterion.py
python -m compileall -q spk_bv_research/native_criterion_v1d.py search/spk_bv_v1d_native_criterion.py
echo '[2/3] Inherited v1c and frozen Architecture v1 guard'
bash search/spk_bv_v1c_research_gate.sh
echo '[3/3] Source-bound v1d native objective requires separate CLI'
echo 'SPK BV v1d NATIVE DECLARED GUARD CRITERION RESEARCH PASS (native evidence separate)'
