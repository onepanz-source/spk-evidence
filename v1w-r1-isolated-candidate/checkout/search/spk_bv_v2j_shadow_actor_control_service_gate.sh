#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <v2i-report.json> <new-v2j-report.json>" >&2
  exit 2
fi

export SPK_V2I_REPORT="$1"

echo '[1/3] BV v2j source-backed shadow-service and adversarial unittest gate'
python -m unittest discover -s tests -p 'test_spk_bv_v2j_shadow_actor_control_service.py' -v

echo '[2/3] BV v2j pinned native full-parity and resource-tail matrix'
python -m search.spk_bv_v2j_shadow_actor_control_service --v2i "$1" --out "$2"

echo '[3/3] BV v2j shadow resource service research gate PASS; native intake BLOCKED'
