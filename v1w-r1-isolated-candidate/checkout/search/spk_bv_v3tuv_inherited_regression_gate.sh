#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] BV v3q-v3s inherited adversarial source/actor custody suite'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v3qrs_actor_service_gap.py' -v
bash search/spk_bv_v3qrs_inherited_regression_gate.sh

echo '[2/2] BV v3t-v3v inherited selected regression gate PASS'
