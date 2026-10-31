#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 6 ]]; then
  echo 'Usage: bash search/spk_bv_v4vwx_candidate_authority_gate.sh V3TUV.json V4JKL.json V4MNO.json V4PQR.json V4STU.json NEW-OUTPUT.json' >&2
  exit 2
fi

export SPK_V3TUV_REPORT="$1"
export SPK_V4JKL_REPORT="$2"
export SPK_V4MNO_REPORT="$3"
export SPK_V4PQR_REPORT="$4"
export SPK_V4STU_REPORT="$5"

echo '[1/7] v4v-v4x ACK-conditioned candidate authority and OOD veto tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4vwx_candidate_authority.py' -v

echo '[2/7] Inherited v4s-v4u paid actor consumer tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4stu_paid_actor_consumer.py' -v

echo '[3/7] Inherited v4p-v4r endogenous native actor ACK tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4pqr_endogenous_actor_ACK.py' -v

echo '[4/7] Inherited v4m-v4o causal native replay tests'
python -m unittest discover -s tests \
  -p 'test_spk_bv_v4mno_native_ACK_causal_replay.py' -v

echo '[5/7] Frozen native original forward/BV smoke witness'
python -c 'from search.spk_bv_v0e_live_evidence import capture; c=capture(); assert c["forward_first"]["forward"]["terminal"] and c["feedback_first"]["feedback"]["link_grants"]; print("v0e source original live dual-scheduler PASS")'

echo '[6/7] Create-only 18 signed native / 18 paid-source / 90 candidate shadow research report'
python -m search.spk_bv_v4vwx_candidate_authority \
  --root "$PWD" --v3tuv "$1" --v4stu "$5" --out "$6"

echo '[7/7] Exact pinned candidate authority/veto observation'
cmp docs/spk-bv-v4vwx-candidate-authority-observation.json "$6"
echo 'v4v-v4x RESEARCH PASS: invalid promotions vetoed; native learner unchanged'
