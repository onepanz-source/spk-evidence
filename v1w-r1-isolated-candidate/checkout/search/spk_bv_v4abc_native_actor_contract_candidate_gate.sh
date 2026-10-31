#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo 'usage: bash search/spk_bv_v4abc_native_actor_contract_candidate_gate.sh SIGNED_V3TUV_JSON NEW_V4ABC_JSON' >&2
  exit 2
fi

echo '[1/4] BV v4a-v4c native service contract candidate, adversarial and conditional-lemma unittest'
SPK_V3TUV_REPORT="$1" python -m unittest discover \
  -s tests -p 'test_spk_bv_v4abc_native_actor_contract_candidate.py' -v

echo '[2/4] BV v4a-v4c signed 72-context native-source exposure and proposal audit'
python -m search.spk_bv_v4abc_native_actor_contract_candidate \
  --v3tuv "$1" --out "$2"

echo '[3/4] BV v4a-v4c source-backed conditional service candidate gate PASS'
echo '[4/4] Native actor rate contract ADMISSION BLOCKED; no native operator or learned state changed'
