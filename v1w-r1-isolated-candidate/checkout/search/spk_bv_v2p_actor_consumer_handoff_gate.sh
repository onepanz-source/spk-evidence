#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: bash $0 <signed-v2o-report.json> <new-v2p-report.json>" >&2
  exit 2
fi

export SPK_V2O_REPORT="$1"

echo '[1/3] BV v2p actor consumer causality, custody and adversarial unittest'
python -m unittest discover -s tests -p 'test_spk_bv_v2p_actor_consumer_handoff.py' -v

echo '[2/3] BV v2p source-pinned native parity, actor ACK FIFO consumption and bounded backlogs'
python -m search.spk_bv_v2p_actor_consumer_handoff --v2o "$1" --out "$2"

echo '[3/3] BV v2p actor ACK consumer handoff research gate PASS; frozen native actor intake BLOCKED'
