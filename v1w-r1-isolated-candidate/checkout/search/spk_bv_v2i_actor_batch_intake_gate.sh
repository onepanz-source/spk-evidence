#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <v2h-report.json> <new-v2i-report.json>" >&2
  exit 2
fi

export SPK_V2H_REPORT="$1"

echo '[1/3] v2i actor-batch intake, causal replay, adversarial unittest gate'
python -m unittest discover -s tests -p 'test_spk_bv_v2i_derived_actor_intake.py' -v

echo '[2/3] v2i source-pinned native/derived intake + loss/pressure matrix'
python -m search.spk_bv_v2i_actor_batch_intake --v2h "$1" --out "$2"

echo '[3/3] BV v2i research gate PASS; frozen native actor intake remains BLOCKED'
