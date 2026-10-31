#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1s separate-channel laboratory and adversarial source custody'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1s_receiver_disclosure_channel.py
python -m compileall -q spk_bv_research/receiver_disclosure_channel_v1s.py search/spk_bv_v1s_receiver_disclosure_channel.py
echo '[2/3] Inherited v1r -> frozen Architecture custody gate'
bash search/spk_bv_v1r_research_gate.sh
echo '[3/3] The full source-bound v1r replay requires a separate fwork CLI run'
echo 'SPK BV v1s SHADOW RECEIVER DISCLOSURE CONTRACT PASS (NO NATIVE AUTHORITY)'
