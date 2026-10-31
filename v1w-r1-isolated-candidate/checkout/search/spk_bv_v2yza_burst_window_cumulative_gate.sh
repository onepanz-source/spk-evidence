#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <signed-v2vwx-report.json> <new-v2yza-report.json>" >&2
  exit 2
fi

export SPK_V2VWX_REPORT="$1"

echo '[1/4] BV v2y real burst delivery, two-PE causal queue contention and adversarial unittest'
python -m unittest discover -s tests -p 'test_spk_bv_v2yza_burst_window_cumulative.py' -v

echo '[2/4] BV v2z 45 original native / 270 actor queue policies and activated finite window'
python -m search.spk_bv_v2yza_burst_window_cumulative --v2vwx "$1" --out "$2"

echo '[3/4] BV v3a 225 five-way causal ablations and signed source/resource custody PASS'
echo '[4/4] Frozen native learning and universal queue liveness CONTRACT BLOCKED'
