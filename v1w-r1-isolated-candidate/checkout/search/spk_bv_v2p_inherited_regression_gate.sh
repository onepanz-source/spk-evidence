#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] BV v2o native causal admission dedicated predecessor regressions'
python -m unittest discover -s tests -p 'test_spk_bv_v2o_native_causal_admission.py' -v

echo '[2/2] BV v2p inherited v2n/v2m/v2l/v2k/v2j/v2i/v2h/v2g/v2f/v2e regressions'
bash search/spk_bv_v2o_inherited_regression_gate.sh

echo 'BV v2p inherited regression gate PASS'
