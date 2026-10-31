#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1i native-silence missing feedback, polarity, boundary and adversarial CLI tests'
python -m pytest -q tests/test_spk_bv_v1i_native_feedback_silence.py
python -m compileall -q spk_bv_research/native_feedback_silence_v1i.py search/spk_bv_v1i_native_feedback_silence.py
echo '[2/3] Inherited BV v1h and frozen Architecture v1 custody gate'
bash search/spk_bv_v1h_research_gate.sh
echo '[3/3] Full source-bound v1h reconstruction and v1i attestation require separate native CLI'
echo 'SPK BV v1i RESEARCH PASS (no endogenous utility or feedback judgment)'
