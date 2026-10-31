#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 8 ]]; then
  echo 'Usage: bash search/spk_bv_v4abad_oracle_custody_gate.sh V3TUV.json V4JKL.json V4MNO.json V4PQR.json V4STU.json V4VWX.json V4YZAA.json NEW-OUTPUT.json' >&2
  exit 2
fi

export SPK_V3TUV_REPORT="$1"
export SPK_V4JKL_REPORT="$2"
export SPK_V4MNO_REPORT="$3"
export SPK_V4PQR_REPORT="$4"
export SPK_V4STU_REPORT="$5"
export SPK_V4VWX_REPORT="$6"
export SPK_V4YZAA_REPORT="$7"

echo '[1/9] v4ab-v4ad typed task oracle custody, two-role test HMAC, poison/adversarial tests'
python -m unittest discover -s tests -p test_spk_bv_v4abad_oracle_custody.py -v

echo '[2/9] Inherited v4y-v4aa external task objective tests'
python -m unittest discover -s tests -p test_spk_bv_v4yzaa_task_objective.py -v

echo '[3/9] Inherited v4v-v4x candidate authority tests'
python -m unittest discover -s tests -p test_spk_bv_v4vwx_candidate_authority.py -v

echo '[4/9] Inherited v4s-v4u paid consumer tests'
python -m unittest discover -s tests -p test_spk_bv_v4stu_paid_actor_consumer.py -v

echo '[5/9] Inherited v4p-v4r native-derived ACK tests'
python -m unittest discover -s tests -p test_spk_bv_v4pqr_endogenous_actor_ACK.py -v

echo '[6/9] Inherited v4m-v4o causal replay tests'
python -m unittest discover -s tests -p test_spk_bv_v4mno_native_ACK_causal_replay.py -v

echo '[7/9] Frozen native original live dual-scheduler smoke witness'
python -c 'from search.spk_bv_v0e_live_evidence import capture; r=capture(); assert r["forward_first"]["forward"]["terminal"] and r["feedback_first"]["feedback"]["link_grants"]; print("v0e original native evidence PASS")'

echo '[8/9] Create-only signed 18 native / 216 oracle provenance research report'
python -m search.spk_bv_v4abad_oracle_custody \
  --root "$PWD" --v3tuv "$1" --v4yzaa "$7" --out "$8"

echo '[9/9] Byte-exact pinned task oracle custody observation'
cmp docs/spk-bv-v4abad-oracle-custody-observation.json "$8"
echo 'v4ab-v4ad RESEARCH PASS: co-signed poison quarantined; no native learner/adoption'
