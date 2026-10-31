#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] v1v frozen scheduler source-bound API surface and adversarial tests'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1v_frozen_observation_surface.py
python -m compileall -q spk_bv_research/frozen_observation_surface_v1v.py search/spk_bv_v1v_frozen_observation_surface.py
echo '[2/3] Inherited v1u full research gate and frozen source custody'
bash search/spk_bv_v1u_research_gate.sh
echo '[3/3] v1v frozen source inspection is CLI-only: no callback, native mailbox, or live receiver authority claimed'
echo 'SPK BV v1v SOURCE-PINNED READONLY OBSERVATION SURFACE AUDIT PASS (NOT LIVE NATIVE BV)'
