#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <v2n-report.json> <new-v2o-report.json>" >&2
  exit 2
fi

export SPK_V2N_REPORT="$1"

echo '[1/3] BV v2o source-backed native causal admission and adversarial unittest'
python -m unittest discover -s tests -p 'test_spk_bv_v2o_native_causal_admission.py' -v

echo '[2/3] BV v2o strict native-causal priority, individual ablations and bounded horizon'
python -m search.spk_bv_v2o_native_causal_admission --v2n "$1" --out "$2"

echo '[3/3] BV v2o derived native causal-ready contract research gate PASS; native consumer BLOCKED'
