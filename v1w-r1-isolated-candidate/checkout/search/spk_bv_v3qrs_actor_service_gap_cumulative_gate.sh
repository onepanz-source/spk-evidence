#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo 'usage: bash search/spk_bv_v3qrs_actor_service_gap_cumulative_gate.sh SIGNED_V3NOP_JSON NEW_V3QRS_JSON' >&2
  exit 2
fi

echo '[1/4] BV v3q-v3s actor-specific source custody, peer wait and adversarial unittest'
SPK_V3NOP_REPORT="$1" python -m unittest discover \
  -s tests -p 'test_spk_bv_v3qrs_actor_service_gap.py' -v

echo '[2/4] BV v3q-v3s 18 native, 72 derived actor, 36 causal-null replays'
python -m search.spk_bv_v3qrs_actor_service_gap_cumulative \
  --v3nop "$1" --out "$2"

echo '[3/4] BV v3q-v3s per-actor source/censor/projection research gate PASS'
echo '[4/4] Universal native per-actor fair scheduler/deadline and learning CONTRACT BLOCKED'
