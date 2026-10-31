#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo 'usage: bash search/spk_bv_v3nop_native_ack_gap_cumulative_gate.sh SIGNED_V3KLM_JSON NEW_V3NOP_JSON' >&2
  exit 2
fi

echo '[1/4] BV v3n-v3p source wait gap, tampering and adversarial unittest'
SPK_V3KLM_REPORT="$1" python -m unittest discover \
  -s tests -p 'test_spk_bv_v3nop_native_ack_gap.py' -v

echo '[2/4] BV v3n-v3p 18 new native source, 72 derived, 36 causal null runs'
python -m search.spk_bv_v3nop_native_ack_gap_cumulative \
  --v3klm "$1" --out "$2"

echo '[3/4] BV v3n-v3p finite source-ready ACK gap partition PASS'
echo '[4/4] Universal actor ACK deadline, native fairness and native learning CONTRACT BLOCKED'
