#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
echo '[1/3] BV v0n observational record occupancy, invariants and CLI adversarial tests'
python -m pytest -q tests/test_spk_bv_v0n_native_occupancy.py
echo '[2/3] Complete inherited BV v0m research gate and Architecture v1 guard'
bash search/spk_bv_v0m_research_gate.sh
echo '[3/3] Actual native report must be observed separately; no hardware/causal claims'
echo 'SPK BV V0n NATIVE OCCUPANCY: RESEARCH PASS (independent local native CLI required)'
