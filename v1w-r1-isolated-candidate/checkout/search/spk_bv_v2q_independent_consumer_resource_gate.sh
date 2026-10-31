#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <signed-v2p-report.json> <new-v2q-report.json>" >&2
  exit 2
fi

export SPK_V2P_REPORT="$1"

echo '[1/3] BV v2q independent PE/memory actor charge and adversarial unittest'
python -m unittest discover -s tests -p 'test_spk_bv_v2q_independent_consumer_resource.py' -v

echo '[2/3] BV v2q signed native 90-cell resource-charged parity and starvation matrix'
python -m search.spk_bv_v2q_independent_consumer_resource --v2p "$1" --out "$2"

echo '[3/3] BV v2q independently charged actor consumer research gate PASS; frozen native actor intake BLOCKED'
