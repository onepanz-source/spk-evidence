#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo '[1/2] BV v0q field-level provenance and negative cases'
python -m pytest -q -p no:cacheprovider tests/test_spk_bv_v0q_lineage.py
echo '[2/2] Original BV v0p identity tests'
python -m pytest -q -p no:cacheprovider tests/test_spk_bv_v0p_policy_identity.py
echo 'SPK BV v0q FIELD-LEVEL FEEDBACK LINEAGE: RESEARCH PASS (not ON/OFF, causal, or learning)'
