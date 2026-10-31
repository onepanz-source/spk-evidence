#!/usr/bin/env bash
set -euo pipefail

echo '[1/3] BV v4d-v4f inherited source/native capacity tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4def_native_capacity_envelope.py' -v

echo '[2/3] BV v4d-v4f inherited v4abc -> v3tuv -> prior regressions'
bash search/spk_bv_v4def_inherited_regression_gate.sh

echo '[3/3] BV v4g-v4i inherited regression gate PASS; native runtime/Architecture v1 frozen'
