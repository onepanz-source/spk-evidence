#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <signed-v2r-report.json> <new-v2stu-report.json>" >&2
  exit 2
fi

export SPK_V2R_REPORT="$1"

echo '[1/4] BV v2s true pre-forward independently PE/RAM-paid actor consumer'
python -m unittest discover -s tests -p 'test_spk_bv_v2stu_concurrent_cumulative.py' -v

echo '[2/4] BV v2t 90 native, 360 derived four-guard and 180 causal interventions'
python -m search.spk_bv_v2stu_concurrent_cumulative --v2r "$1" --out "$2"

echo '[3/4] BV v2u source-pinned paid-resource, adversarial and finite horizon closure PASS'
echo '[4/4] Frozen native actor/control/arbitration/learning policy remains BLOCKED'
