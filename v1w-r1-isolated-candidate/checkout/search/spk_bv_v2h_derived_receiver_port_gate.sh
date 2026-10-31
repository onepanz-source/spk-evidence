#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ "$#" -ne 2 ]]; then
  echo "usage: bash search/spk_bv_v2h_derived_receiver_port_gate.sh /tmp/v2g.json /tmp/v2h.json" >&2
  exit 2
fi
echo '[1/3] v2h source-backed actor port and adversarial unittest gate'
SPK_V2G_REPORT="$1" python -m unittest discover -s tests -p test_spk_bv_v2h_derived_receiver_port.py -v
echo '[2/3] v2h pinned native/derived full parity and feedback intervention matrix'
python -m search.spk_bv_v2h_derived_receiver_port --v2g "$1" --out "$2"
echo '[3/3] BV v2h derived actor port research gate PASS (frozen native actor intake remains BLOCKED)'
