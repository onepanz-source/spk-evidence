#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 3 ]]; then
  echo 'Usage: bash search/spk_bv_v4mno_native_ACK_causal_gate.sh V3TUV.json V4JKL.json NEW-OUTPUT.json' >&2
  exit 2
fi

# The unittest source locator must see exactly the same signed predecessors
# as the create-only command, even when reports live under ~/Scaricati.
export SPK_V3TUV_REPORT="$1"
export SPK_V4JKL_REPORT="$2"

echo '[1/4] v4m-v4o native causal reexecution, provenance and adversarial tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4mno_native_ACK_causal_replay.py' -v

echo '[2/4] Signed v3tuv/v4jkl source and create-only native causal replay'
python -m search.spk_bv_v4mno_native_ACK_causal_replay \
  --root "$PWD" --v3tuv "$1" --v4jkl "$2" --out "$3"

echo '[3/4] Exact pinned reference observation comparison'
cmp docs/spk-bv-v4mno-native-ACK-causal-observation.json "$3"

echo '[4/4] RESEARCH-only causal replay PASS; actor credit/learning NOT IMPLEMENTED'
