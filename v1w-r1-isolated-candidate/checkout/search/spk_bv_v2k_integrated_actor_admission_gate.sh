#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <v2j-report.json> <new-v2k-report.json>" >&2
  exit 2
fi

export SPK_V2J_REPORT="$1"

echo '[1/3] BV v2k integrated DERIVED resource counter and adversarial unittest gate'
python -m unittest discover -s tests -p 'test_spk_bv_v2k_integrated_actor_admission.py' -v

echo '[2/3] BV v2k pinned native/full projection and resource mutation matrix'
python -m search.spk_bv_v2k_integrated_actor_admission --v2j "$1" --out "$2"

echo '[3/3] BV v2k derived resource-counter admission PASS; native actor event policy BLOCKED'
