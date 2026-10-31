#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo '[1/2] BV v0r semantic signature matching, ambiguity and adversarial CLI tests'
python -m pytest -q -p no:cacheprovider tests/test_spk_bv_v0r_semantic_pairing.py
echo '[2/2] Inherited BV v0p/v0q differential tests'
python -m pytest -q -p no:cacheprovider tests/test_spk_bv_v0p_policy_identity.py tests/test_spk_bv_v0q_lineage.py
echo 'SPK BV v0r SEMANTIC FEEDBACK SIGNATURES: RESEARCH PASS (no causal equivalence, no ON/OFF)'
