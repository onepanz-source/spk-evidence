#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1k receiver-local expectation and witness-authority negative controls'
python -m pytest -q tests/test_spk_bv_v1k_witness_authority.py
python -m compileall -q spk_bv_research/receiver_witness_boundary_v1k.py search/spk_bv_v1k_witness_authority.py
echo '[2/3] Inherited BV v1j and frozen Architecture v1 custody research gate'
bash search/spk_bv_v1j_research_gate.sh
echo '[3/3] Native source recomputation and optional shadow protocol require separate CLI'
echo 'SPK BV v1k WITNESS AUTHORITY BOUNDARY RESEARCH PASS (no native absence witnesses or learning)'
