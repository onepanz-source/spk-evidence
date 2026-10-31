#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] BV v2r dedicated three-way causal priority and predecessor chain'
python -m unittest discover -s tests -p 'test_spk_bv_v2r_three_way_causal_priority.py' -v
bash search/spk_bv_v2r_inherited_regression_gate.sh

echo '[2/2] BV v2s-v2u cumulative inherited regression gate PASS'
