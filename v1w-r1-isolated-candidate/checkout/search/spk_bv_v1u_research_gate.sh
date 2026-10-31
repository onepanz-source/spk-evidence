#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1u bounded incremental lab control-channel & adversarial receiver tests'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1u_incremental_shadow_channel.py
python -m compileall -q spk_bv_research/incremental_shadow_channel_v1u.py search/spk_bv_v1u_incremental_shadow_channel.py
echo '[2/3] Inherited source-bound gate (including native frozen source custody)'
bash search/spk_bv_v1t_research_gate.sh
echo '[3/3] New native replay is CLI-only; v1u has NO frozen scheduler callback or native control transport'
echo 'SPK BV v1u BOUNDED INCREMENTAL SHADOW CHANNEL PASS (NOT NATIVE LIVE BV)'
