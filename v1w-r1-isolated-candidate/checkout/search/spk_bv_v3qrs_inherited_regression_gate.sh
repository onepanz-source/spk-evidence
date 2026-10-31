#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] BV v3n-v3p inherited source ready gap and adversarial suite'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v3nop_native_ack_gap.py' -v
bash search/spk_bv_v3nop_inherited_regression_gate.sh

echo '[2/2] BV v3q-v3s inherited selected regression gate PASS'
