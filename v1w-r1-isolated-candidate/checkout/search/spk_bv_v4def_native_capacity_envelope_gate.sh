#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo 'usage: bash search/spk_bv_v4def_native_capacity_envelope_gate.sh SIGNED_V3TUV_JSON SIGNED_V4ABC_JSON NEW_V4DEF_JSON' >&2
  exit 2
fi

echo '[1/4] BV v4d-v4f native PE/memory replay audit and adversarial unittest'
SPK_V3TUV_REPORT="$1" SPK_V4ABC_REPORT="$2" \
  python -m unittest discover \
  -s tests -p 'test_spk_bv_v4def_native_capacity_envelope.py' -v

echo '[2/4] BV v4d-v4f signed 18 native replays, 72 ACK contexts, capacity envelope'
python -m search.spk_bv_v4def_native_capacity_envelope \
  --v3tuv "$1" --v4abc "$2" --out "$3"

echo '[3/4] BV v4d-v4f source-native capacity envelope and counterexample gate PASS'
echo '[4/4] Native ACK reservation, forward re-arbitration, deadlines and learning NOT IMPLEMENTED'
