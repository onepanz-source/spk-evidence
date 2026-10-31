#!/usr/bin/env bash
set -euo pipefail

echo '[1/3] BV v4g-v4i inherited source-native coverage frontier tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4ghi_native_coverage_frontier.py' -v

echo '[2/3] BV v4g-v4i inherited v4def -> v4abc -> v3tuv -> prior regressions'
bash search/spk_bv_v4ghi_inherited_regression_gate.sh

echo '[3/3] BV v4j-v4l inherited regression PASS; no change to frozen Architecture/native'
