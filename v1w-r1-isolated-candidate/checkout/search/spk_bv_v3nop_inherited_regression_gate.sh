#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] BV v3k-v3m inherited signed ACK opportunity and adversarial suite'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v3klm_native_ack_opportunity.py' -v
bash search/spk_bv_v3klm_inherited_regression_gate.sh

echo '[2/2] BV v3n-v3p inherited selected regression gate PASS'
