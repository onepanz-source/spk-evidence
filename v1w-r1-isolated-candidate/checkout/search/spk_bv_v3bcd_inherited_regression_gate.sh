#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] BV v2y-v3a inherited finite two-turn source burst regressions'
python -m unittest discover -s tests -p 'test_spk_bv_v2yza_burst_window_cumulative.py' -v
bash search/spk_bv_v2yza_inherited_regression_gate.sh

echo '[2/2] BV v3b-v3d cumulative inherited regression gate PASS'
