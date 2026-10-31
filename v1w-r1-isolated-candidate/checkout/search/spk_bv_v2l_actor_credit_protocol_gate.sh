#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <v2k-report.json> <new-v2l-report.json>" >&2
  exit 2
fi

export SPK_V2K_REPORT="$1"

echo '[1/3] BV v2l derived actor credit journal, causal custody and adversarial unittest'
python -m unittest discover -s tests -p 'test_spk_bv_v2l_actor_credit_protocol.py' -v

echo '[2/3] BV v2l signed v2k resource parity, full native projection and bounded credit matrix'
python -m search.spk_bv_v2l_actor_credit_protocol --v2k "$1" --out "$2"

echo '[3/3] BV v2l derived causal credit/ack research gate PASS; frozen native actor contract BLOCKED'
