#!/usr/bin/env bash
set -euo pipefail

echo '[1/3] BV v4a-v4c inherited candidate-contract gate tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4abc_native_actor_contract_candidate.py' -v

echo '[2/3] BV v4a-v4c inherited source FIFO and previous regression chain'
bash search/spk_bv_v4abc_inherited_regression_gate.sh

echo '[3/3] BV v4d-v4f inherited gate PASS, Architecture v1 and native runtime remain frozen'
