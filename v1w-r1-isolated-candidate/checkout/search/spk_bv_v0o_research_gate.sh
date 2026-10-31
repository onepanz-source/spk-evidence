#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
echo '[1/3] Complete inherited v0n research gate and frozen Architecture v1 guard'
bash search/spk_bv_v0n_research_gate.sh
echo '[2/3] BV v0o source-bound native paired-runs fixture and adversarial comparator tests'
python -m pytest -q tests/test_spk_bv_v0o_paired_runs.py
echo '[3/3] Native v0e run fixture comparison requires independent capture and inspection'
echo 'SPK BV V0o PAIRED NATIVE RUN DISCOVERY: RESEARCH PASS (equal workload NOT yet established)'
