#!/usr/bin/env bash
set -euo pipefail

echo '[1/3] v4j-v4l inherited native ACK shadow-PE arbiter tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4jkl_native_ACK_shadow_arbiter.py' -v

echo '[2/3] Full inherited v4ghi -> v4def -> v3tuv -> earlier regressions'
bash search/spk_bv_v4jkl_inherited_regression_gate.sh

echo '[3/3] v4m-v4o inherited regression PASS; frozen source unchanged'
