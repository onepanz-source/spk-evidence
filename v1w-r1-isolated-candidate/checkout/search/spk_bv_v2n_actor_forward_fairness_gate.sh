#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <v2m-report.json> <new-v2n-report.json>" >&2
  exit 2
fi

export SPK_V2M_REPORT="$1"

echo '[1/3] BV v2n bounded forward protection and adversarial unittest gate'
python -m unittest discover -s tests -p 'test_spk_bv_v2n_actor_forward_fairness.py' -v

echo '[2/3] BV v2n signed v2m/native and actor fairness window differential matrix'
python -m search.spk_bv_v2n_actor_forward_fairness --v2m "$1" --out "$2"

echo '[3/3] BV v2n derived forward budget opportunity PASS; universal native liveness CONTRACT BLOCKED'
