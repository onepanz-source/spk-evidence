#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] BV v2v-v2x inherited finite queue and source chain unittest'
python -m unittest discover -s tests -p 'test_spk_bv_v2vwx_queue_precedence_cumulative.py' -v
bash search/spk_bv_v2vwx_inherited_regression_gate.sh

echo '[2/2] BV v2y-v3a cumulative inherited regression gate PASS'
