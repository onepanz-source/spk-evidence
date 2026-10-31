#!/usr/bin/env bash
set -euo pipefail

echo '[1/2] BV v3e-v3g inherited guard factorial, ACK waits and source-tail regressions'
python -m unittest discover -s tests -p 'test_spk_bv_v3efg_native_veto_attribution.py' -v
bash search/spk_bv_v3efg_inherited_regression_gate.sh

echo '[2/2] BV v3h-v3j inherited selected regression gate PASS'
