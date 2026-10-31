#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] BV v2q independent consumer resource dedicated predecessor regressions'
python -m unittest discover -s tests -p 'test_spk_bv_v2q_independent_consumer_resource.py' -v

echo '[2/2] BV v2r inherited v2p/v2o/v2n/v2m/v2l/v2k/v2j/v2i/v2h/v2g/v2f/v2e regressions'
bash search/spk_bv_v2q_inherited_regression_gate.sh

echo 'BV v2r inherited regression gate PASS'
