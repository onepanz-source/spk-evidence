#!/usr/bin/env bash
set -euo pipefail

echo
echo "======================================================================"
echo "SPK DOMAIN PREMISES FINAL GATE v0"
echo "======================================================================"

echo
echo "[1/8] SOURCE_DEFINED family"
python -m search.core_domain_source_defined_family_v0

echo
echo "[2/8] TARGET_DEFINED / D-TIME-05"
python -m search.core_domain_time05_target_defined_v0

echo
echo "[3/8] BOTH_DEFINED / D-RESET-01"
python -m search.core_domain_reset01_both_defined_v0

echo
echo "[4/8] ABSTRACT_BOUND / D-TIME-01"
python -m search.core_domain_time01_abstract_bound_v0

echo
echo "[5/8] premise ledger"
python -m search.core_domain_premises_v0

echo
echo "[6/8] DOMAIN definedness census"
python -m search.core_domain_definedness_v0

echo
echo "[7/8] global rule soundness"
python -m search.core_rule_soundness_v0

echo
echo "[8/8] pytest"
pytest -q

echo
echo "======================================================================"
echo "SPK DOMAIN PREMISES FINAL GATE: PASS"
echo "======================================================================"
