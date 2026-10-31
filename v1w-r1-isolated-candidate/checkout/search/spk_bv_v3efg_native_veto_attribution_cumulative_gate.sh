#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <signed-v3bcd-report.json> <new-v3efg-report.json>" >&2
  exit 2
fi

export SPK_V3BCD_REPORT="$1"

echo '[1/4] BV v3e-v3g source-native veto factorial and adversarial unittest'
python -m unittest discover -s tests -p 'test_spk_bv_v3efg_native_veto_attribution.py' -v

echo '[2/4] BV v3e/v3f 27 native, 324 derived 2x2 guards, exact ACK wait partition'
python -m search.spk_bv_v3efg_native_veto_attribution_cumulative \
  --v3bcd "$1" --out "$2"

echo '[3/4] BV v3g 54 causal null and 27 explicit no-tail differential runs PASS'
echo '[4/4] Native universal ACK progress and actor learning CONTRACT BLOCKED'
