#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] BV v2s-v2u dedicated source-backed concurrent consumer regressions'
python -m unittest discover -s tests -p 'test_spk_bv_v2stu_concurrent_cumulative.py' -v
bash search/spk_bv_v2stu_inherited_regression_gate.sh

echo '[2/2] BV v2v-v2x cumulative inherited regression gate PASS'
