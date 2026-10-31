#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 9 ]]; then
  echo 'Usage: bash search/spk_bv_v4aeag_two_view_adjudication_gate.sh V3TUV.json V4JKL.json V4MNO.json V4PQR.json V4STU.json V4VWX.json V4YZAA.json V4ABAD.json NEW-OUTPUT.json' >&2
  exit 2
fi

export SPK_V3TUV_REPORT="$1"
export SPK_V4JKL_REPORT="$2"
export SPK_V4MNO_REPORT="$3"
export SPK_V4PQR_REPORT="$4"
export SPK_V4STU_REPORT="$5"
export SPK_V4VWX_REPORT="$6"
export SPK_V4YZAA_REPORT="$7"
export SPK_V4ABAD_REPORT="$8"

echo '[1/10] v4ae-v4ag correlated two-view evidence, disagreement escrow and adversarial tests'
python -m unittest discover -s tests -p test_spk_bv_v4aeag_two_view_adjudication.py -v

echo '[2/10] Inherited v4ab-v4ad dual-attested synthetic task oracle custody'
python -m unittest discover -s tests -p test_spk_bv_v4abad_oracle_custody.py -v

echo '[3/10] Inherited v4y-v4aa external synthetic task objective'
python -m unittest discover -s tests -p test_spk_bv_v4yzaa_task_objective.py -v

echo '[4/10] Inherited v4v-v4x derived candidate authority boundary'
python -m unittest discover -s tests -p test_spk_bv_v4vwx_candidate_authority.py -v

echo '[5/10] Inherited v4s-v4u paid actor consumer'
python -m unittest discover -s tests -p test_spk_bv_v4stu_paid_actor_consumer.py -v

echo '[6/10] Inherited v4p-v4r endogenous actor ACK feedback'
python -m unittest discover -s tests -p test_spk_bv_v4pqr_endogenous_actor_ACK.py -v

echo '[7/10] Inherited v4m-v4o causal native ACK replay'
python -m unittest discover -s tests -p test_spk_bv_v4mno_native_ACK_causal_replay.py -v

echo '[8/10] Frozen native v0e forward and BV dual scheduling smoke witness'
python -c 'from search.spk_bv_v0e_live_evidence import capture; r=capture(); assert r["forward_first"]["forward"]["terminal"] and r["feedback_first"]["feedback"]["link_grants"]; print("frozen native v0e smoke PASS")'

echo '[9/10] Source-pinned native and two-view research report, create-only'
python -m search.spk_bv_v4aeag_two_view_adjudication \
  --root "$PWD" --v3tuv "$1" --v4abad "$8" --out "$9"

echo '[10/10] Byte-exact comparison to independently pinned bounded observation'
cmp docs/spk-bv-v4aeag-two-view-observation.json "$9"
echo 'v4ae-v4ag RESEARCH PASS: disagreement escrow; two-view unanimity still not task truth; zero adoption'
