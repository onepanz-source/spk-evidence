#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
echo '[1/3] BV v0m source-bound grant/delivery pairing contract and CLI adversarial tests'
python -m pytest -q tests/test_spk_bv_v0m_native_packet_pairing.py
echo '[2/3] Complete inherited BV v0l/v0k research gate and Architecture v1 guard'
bash search/spk_bv_v0l_research_gate.sh
echo '[3/3] Actual fixture must be analyzed separately; no v0h equivalence claim'
echo 'SPK BV V0m SOURCE-BOUND PACKET/GRANT RECORD PAIRING: RESEARCH PASS (real pairing CLI is separate)'
