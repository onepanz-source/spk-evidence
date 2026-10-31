#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo 'usage: bash search/spk_bv_v4ghi_native_coverage_frontier_gate.sh SIGNED_V3TUV_JSON SIGNED_V4ABC_JSON SIGNED_V4DEF_JSON NEW_V4GHI_JSON' >&2
  exit 2
fi

echo '[1/4] BV v4g-v4i exact native opportunity coverage and brute force adversarial tests'
SPK_V3TUV_REPORT="$1" SPK_V4ABC_REPORT="$2" SPK_V4DEF_REPORT="$3" \
  python -m unittest discover \
  -s tests -p 'test_spk_bv_v4ghi_native_coverage_frontier.py' -v

echo '[2/4] BV v4g-v4i source-native signed replay and interval coverage frontier'
python -m search.spk_bv_v4ghi_native_coverage_frontier \
  --v3tuv "$1" --v4abc "$2" --v4def "$3" --out "$4"

echo '[3/4] BV v4g-v4i exact bounded coverage math and source-native conservations PASS'
echo '[4/4] Native ACK reservation, prospective service admission, preemption and learning NOT IMPLEMENTED'
