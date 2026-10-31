#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 7 ]]; then
  echo 'Usage: bash search/spk_bv_v4yzaa_task_objective_gate.sh V3TUV.json V4JKL.json V4MNO.json V4PQR.json V4STU.json V4VWX.json NEW-OUTPUT.json' >&2
  exit 2
fi

export SPK_V3TUV_REPORT="$1"
export SPK_V4JKL_REPORT="$2"
export SPK_V4MNO_REPORT="$3"
export SPK_V4PQR_REPORT="$4"
export SPK_V4STU_REPORT="$5"
export SPK_V4VWX_REPORT="$6"

echo '[1/8] v4y-v4aa external objective and adversarial custody tests'
python -m unittest discover -s tests -p test_spk_bv_v4yzaa_task_objective.py -v

echo '[2/8] Inherited v4v-v4x actor candidate authority tests'
python -m unittest discover -s tests -p test_spk_bv_v4vwx_candidate_authority.py -v

echo '[3/8] Inherited v4s-v4u paid actor consumer tests'
python -m unittest discover -s tests -p test_spk_bv_v4stu_paid_actor_consumer.py -v

echo '[4/8] Inherited v4p-v4r endogenous actor ACK tests'
python -m unittest discover -s tests -p test_spk_bv_v4pqr_endogenous_actor_ACK.py -v

echo '[5/8] Inherited v4m-v4o native causal replay tests'
python -m unittest discover -s tests -p test_spk_bv_v4mno_native_ACK_causal_replay.py -v

echo '[6/8] Frozen native original live dual-scheduler smoke witness'
python -c 'from search.spk_bv_v0e_live_evidence import capture; r=capture(); assert r["forward_first"]["forward"]["terminal"] and r["feedback_first"]["feedback"]["link_grants"]; print("v0e original native evidence PASS")'

echo '[7/8] Create-only signed, independently audited 18+126 objective research report'
python -m search.spk_bv_v4yzaa_task_objective \
  --root "$PWD" --v3tuv "$1" --v4vwx "$6" --out "$7"

echo '[8/8] Byte-exact pinned external task objective observation'
cmp docs/spk-bv-v4yzaa-task-objective-observation.json "$7"
echo 'v4y-v4aa RESEARCH PASS: task loss distinct from ACK; no learner, no adoption'
