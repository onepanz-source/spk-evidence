#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1w bounded frozen observation candidate and integration-contract adversarial tests'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1w_observation_seam.py
python -m compileall -q spk_bv_research/observation_seam_contract_v1w.py search/spk_bv_v1w_observation_seam.py
echo '[2/3] Inherited v1v full frozen-source research custody gate'
bash search/spk_bv_v1v_research_gate.sh
echo '[3/3] v1w research-only static seam: no native hook, channel or learning asserted'
echo 'SPK BV v1w READONLY ADDITIVE OBSERVATION SEAM CONTRACT PASS (NOT NATIVE LIVE BV)'
