#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  echo 'usage: bash search/spk_bv_v4jkl_native_ACK_shadow_arbiter_gate.sh SIGNED_V3TUV_JSON SIGNED_V4ABC_JSON SIGNED_V4DEF_JSON SIGNED_V4GHI_JSON NEW_V4JKL_JSON' >&2
  exit 2
fi

echo '[1/4] BV v4j-v4l typed native forward/BV services, PE/memory and adversarial tests'
SPK_V3TUV_REPORT="$1" SPK_V4ABC_REPORT="$2" SPK_V4DEF_REPORT="$3" SPK_V4GHI_REPORT="$4" \
  python -m unittest discover \
    -s tests -p 'test_spk_bv_v4jkl_native_ACK_shadow_arbiter.py' -v

echo '[2/4] BV v4j-v4l signed source native replay and shadow slot ledger'
python -m search.spk_bv_v4jkl_native_ACK_shadow_arbiter \
  --v3tuv "$1" --v4abc "$2" --v4def "$3" --v4ghi "$4" --out "$5"

echo '[3/4] BV v4j-v4l strict-vs-conditional counterfactual slot evidence PASS'
echo '[4/4] Native donor rescheduling, real ACK admission and learning NOT IMPLEMENTED'
