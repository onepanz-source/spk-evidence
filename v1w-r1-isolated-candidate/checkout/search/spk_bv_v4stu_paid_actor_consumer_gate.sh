#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 5 ]]; then
  echo 'Usage: bash search/spk_bv_v4stu_paid_actor_consumer_gate.sh V3TUV.json V4JKL.json V4MNO.json V4PQR.json NEW-OUTPUT.json' >&2
  exit 2
fi

export SPK_V3TUV_REPORT="$1"
export SPK_V4JKL_REPORT="$2"
export SPK_V4MNO_REPORT="$3"
export SPK_V4PQR_REPORT="$4"

echo '[1/6] v4s-v4u causal paid derived actor consumer and independent ledger/adversarial tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4stu_paid_actor_consumer.py' -v

echo '[2/6] Inherited v4p-v4r endogenous actor native reexecution tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4pqr_endogenous_actor_ACK.py' -v

echo '[3/6] Inherited v4m-v4o causal native transport reexecution tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4mno_native_ACK_causal_replay.py' -v

echo '[4/6] Frozen v0e native dual-priority scheduler live smoke witness'
python -c 'from search.spk_bv_v0e_live_evidence import capture; c=capture(); assert c["forward_first"]["forward"]["terminal"] and c["feedback_first"]["feedback"]["link_grants"]; print("v0e source native dual-scheduler PASS")'

echo '[5/6] Create-only source-pinned 18 original / 90 derived causal research report'
python -m search.spk_bv_v4stu_paid_actor_consumer \
  --root "$PWD" --v3tuv "$1" --v4pqr "$4" --out "$5"

echo '[6/6] Exact observation, paid PE/S conservation and frozen-native boundary'
cmp docs/spk-bv-v4stu-paid-actor-consumer-observation.json "$5"
echo 'v4s-v4u RESEARCH PASS: paid derived actor consumers, native learning NOT implemented'
