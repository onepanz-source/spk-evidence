#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo '[1/2] BV v1b read-only native operator replay and adversarial custody tests'
python -m pytest -q tests/test_spk_bv_v1b_native_operator_replay.py
python -m compileall -q spk_bv_research/native_operator_replay_v1b.py search/spk_bv_v1b_native_operator_replay.py
echo '[2/2] Inherited BV v1a research gate'
bash search/spk_bv_v1a_research_gate.sh
printf '%s\n' 'SPK BV v1b NATIVE OPERATOR REPLAY RESEARCH PASS (native replay requires separate CLI)'
