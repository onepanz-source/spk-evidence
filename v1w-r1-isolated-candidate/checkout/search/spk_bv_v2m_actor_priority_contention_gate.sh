#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <v2l-report.json> <new-v2m-report.json>" >&2
  exit 2
fi

export SPK_V2L_REPORT="$1"

echo '[1/3] BV v2m source-pinned pre-forward priority, contention and adversarial unittest'
python -m unittest discover -s tests -p 'test_spk_bv_v2m_actor_priority_contention.py' -v

echo '[2/3] BV v2m original/contended PE-capacity and causal-null native differential matrix'
python -m search.spk_bv_v2m_actor_priority_contention --v2l "$1" --out "$2"

echo '[3/3] BV v2m derived actor-first competition research gate PASS; native event priority CONTRACT BLOCKED'
