#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <signed-v2q-report.json> <new-v2r-report.json>" >&2
  exit 2
fi

export SPK_V2Q_REPORT="$1"

echo '[1/3] BV v2r source causal-priority, independent consumer and adversarial unittest'
python -m unittest discover -s tests -p 'test_spk_bv_v2r_three_way_causal_priority.py' -v

echo '[2/3] BV v2r signed four native-ready guards, 720 causal interventions, finite horizon'
python -m search.spk_bv_v2r_three_way_causal_priority --v2q "$1" --out "$2"

echo '[3/3] BV v2r three-way causal discrimination research PASS; frozen native concurrent arbiter BLOCKED'
