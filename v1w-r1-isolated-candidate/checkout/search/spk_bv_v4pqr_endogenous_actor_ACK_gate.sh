#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 4 ]]; then
  echo 'Usage: bash search/spk_bv_v4pqr_endogenous_actor_ACK_gate.sh V3TUV.json V4JKL.json V4MNO.json NEW-OUTPUT.json' >&2
  exit 2
fi

export SPK_V3TUV_REPORT="$1"
export SPK_V4JKL_REPORT="$2"
export SPK_V4MNO_REPORT="$3"

echo '[1/5] v4p-v4r native-derived semantic actor / causal ACK / credit tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4pqr_endogenous_actor_ACK.py' -v

echo '[2/5] Inherited v4m-v4o full causal native replay gate tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4mno_native_ACK_causal_replay.py' -v

echo '[3/5] Frozen v0e original live dual-scheduler source-backed smoke witness'
python -c 'from search.spk_bv_v0e_live_evidence import capture; c=capture(); assert c["forward_first"]["forward"]["terminal"] and c["feedback_first"]["feedback"]["link_grants"]; print("source-backed v0e forward and BV dual execution PASS")'

echo '[4/5] Create-only bounded endogenous actor reexecution report'
python -m search.spk_bv_v4pqr_endogenous_actor_ACK \
  --root "$PWD" --v3tuv "$1" --v4mno "$3" --out "$4"

echo '[5/5] Exact pinned observation and negative / native boundary PASS'
cmp docs/spk-bv-v4pqr-endogenous-actor-ACK-observation.json "$4"
echo 'v4p-v4r RESEARCH PASS: native learner/frozen architecture unchanged'
