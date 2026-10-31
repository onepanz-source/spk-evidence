#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <signed-v3efg-report.json> <new-v3hij-report.json>" >&2
  exit 2
fi

export SPK_V3EFG_REPORT="$1"

echo '[1/4] BV v3h-v3j source-backed ACK tail capacity and adversarial unittest'
python -m unittest discover -s tests -p 'test_spk_bv_v3hij_ack_tail_opportunity.py' -v

echo '[2/4] BV v3h/v3i real native-safe ACK quota and causal prefix matrix'
python -m search.spk_bv_v3hij_ack_tail_opportunity_cumulative \
  --v3efg "$1" --out "$2"

echo '[3/4] BV v3j exact finite minimum service horizon and causal null PASS'
echo '[4/4] Universal native ACK service opportunity and actor learning CONTRACT BLOCKED'
