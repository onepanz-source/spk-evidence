#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] BV v3h-v3j inherited ACK tail, strict native projection and adversarial tests'
python -m unittest discover -s tests -p 'test_spk_bv_v3hij_ack_tail_opportunity.py' -v
bash search/spk_bv_v3hij_inherited_regression_gate.sh

echo '[2/2] BV v3k-v3m inherited selected regression gate PASS'
