#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1j event-only receiver observability, absence conditions, adversarial and CLI tests'
python -m pytest -q tests/test_spk_bv_v1j_silence_observability.py
python -m compileall -q spk_bv_research/receiver_silence_observability_v1j.py search/spk_bv_v1j_silence_observability.py
echo '[2/3] Full inherited BV v1i and frozen Architecture v1 custody gate'
bash search/spk_bv_v1i_research_gate.sh
echo '[3/3] Native v1i reexecution and event-only coverage audit require separate CLI'
echo 'SPK BV v1j OBSERVABILITY RESEARCH GATE PASS (no absence judgment, no learning)'
