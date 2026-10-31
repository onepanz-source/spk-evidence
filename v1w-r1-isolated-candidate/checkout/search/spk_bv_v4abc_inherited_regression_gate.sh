#!/usr/bin/env bash
set -euo pipefail

echo '[1/3] BV v3t-v3v inherited source FIFO exact rank and adversarial suite'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v3tuv_grant_rank.py' -v

echo '[2/3] BV v3t-v3v inherited regression chain (through v3q-v3s and earlier)'
bash search/spk_bv_v3tuv_inherited_regression_gate.sh

echo '[3/3] BV v4a-v4c inherited regression gate PASS; frozen native unchanged'
