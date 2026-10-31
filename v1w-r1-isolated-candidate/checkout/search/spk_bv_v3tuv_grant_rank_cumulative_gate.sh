#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo 'usage: bash search/spk_bv_v3tuv_grant_rank_cumulative_gate.sh SIGNED_V3QRS_JSON NEW_V3TUV_JSON' >&2
  exit 2
fi

echo '[1/4] BV v3t-v3v source FIFO prefix/rank and adversarial unittest'
SPK_V3QRS_REPORT="$1" python -m unittest discover \
  -s tests -p 'test_spk_bv_v3tuv_grant_rank.py' -v

echo '[2/4] BV v3t-v3v 18 native, 72 derived, 36 causal-null source replays'
python -m search.spk_bv_v3tuv_grant_rank_cumulative \
  --v3qrs "$1" --out "$2"

echo '[3/4] BV v3t-v3v exact conditional source FIFO/grant rank gate PASS'
echo '[4/4] Native clock deadline, service rate, fairness and learning CONTRACT BLOCKED'
