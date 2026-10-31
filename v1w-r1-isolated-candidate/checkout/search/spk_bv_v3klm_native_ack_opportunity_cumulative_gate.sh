#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo 'usage: bash search/spk_bv_v3klm_native_ack_opportunity_cumulative_gate.sh SIGNED_V3HIJ_JSON NEW_REPORT_JSON' >&2
  exit 2
fi

echo '[1/4] BV v3k-v3m native-safe conditional ACK service and adversarial unittest'
SPK_V3HIJ_REPORT="$1" python -m unittest discover \
  -s tests -p 'test_spk_bv_v3klm_native_ack_opportunity.py' -v

echo '[2/4] BV v3k/v3l 54 native, 216 actor priority/PE/quota and 108 causal null replays'
python -m search.spk_bv_v3klm_native_ack_opportunity_cumulative \
  --v3hij "$1" --out "$2"

echo '[3/4] BV v3m source-conditional ACK opportunity and queue inversion gate PASS'
echo '[4/4] Universal native scheduling fairness, ACK deadline and actor learning CONTRACT BLOCKED'
