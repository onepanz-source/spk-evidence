#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 13 ]]; then
  echo 'Usage: bash search/spk_bv_v4akam_external_anchor_gate.sh V3TUV.json V4JKL.json V4MNO.json V4PQR.json V4STU.json V4VWX.json V4YZAA.json V4ABAD.json V4AEAG.json V4AHAJ.sqlite V4AHAJ.json NEW-ANCHOR.json NEW-AUDIT.json' >&2
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
export SPK_V4AEAG_REPORT="$9"
export SPK_V4AHAJ_REPORT="${11}"

echo '[1/12] v4ak-v4am valid divergent fork, independently pinned head and rollback research tests'
python -m unittest discover -s tests -p test_spk_bv_v4akam_external_anchor.py -v

echo '[2/12] Inherited v4ah-v4aj crash/restart transactional SQLite escrow tests'
python -m unittest discover -s tests -p test_spk_bv_v4ahaj_persistent_escrow.py -v

echo '[3/12] Inherited v4ae-v4ag correlated two-view disagreement/abstention tests'
python -m unittest discover -s tests -p test_spk_bv_v4aeag_two_view_adjudication.py -v

echo '[4/12] Inherited v4ab-v4ad attested synthetic task oracle custody'
python -m unittest discover -s tests -p test_spk_bv_v4abad_oracle_custody.py -v

echo '[5/12] Inherited v4y-v4aa synthetic task objective'
python -m unittest discover -s tests -p test_spk_bv_v4yzaa_task_objective.py -v

echo '[6/12] Inherited v4v-v4x candidate-authority boundary'
python -m unittest discover -s tests -p test_spk_bv_v4vwx_candidate_authority.py -v

echo '[7/12] Inherited v4s-v4u paid actor consumer'
python -m unittest discover -s tests -p test_spk_bv_v4stu_paid_actor_consumer.py -v

echo '[8/12] Inherited v4p-v4r endogenous actor ACK'
python -m unittest discover -s tests -p test_spk_bv_v4pqr_endogenous_actor_ACK.py -v

echo '[9/12] Inherited v4m-v4o native ACK causal replay'
python -m unittest discover -s tests -p test_spk_bv_v4mno_native_ACK_causal_replay.py -v

echo '[10/12] Frozen v0e native forward/BV two-scheduler smoke'
python -c 'from search.spk_bv_v0e_live_evidence import capture; r=capture(); assert r["forward_first"]["forward"]["terminal"] and r["feedback_first"]["feedback"]["link_grants"]; print("frozen native v0e smoke PASS")'

echo '[11/12] Source-pinned escrow verification and create-only outside-head fixture and research audit'
python -m search.spk_bv_v4akam_external_anchor \
  --root "$PWD" --v4ahaj "${11}" --db "${10}" \
  --anchor-out "${12}" --out "${13}"

echo '[12/12] Byte-exact reference and divergent-fork/rollback proof checked against held head'
cmp docs/spk-bv-v4akam-anchor-fixture.json "${12}"
cmp docs/spk-bv-v4akam-external-anchor-observation.json "${13}"
python - "${10}" "${12}" "${13}" <<'PY'
import json
from pathlib import Path
import sys
from spk_bv_research.task_anchor_fixture_v4akam import TEST_ANCHOR_KEY
from spk_bv_research.task_anchor_v4akam import check_anchored_database
db, anchor, output = map(Path, sys.argv[1:])
report = json.loads(output.read_bytes())
state = check_anchored_database(
    db, report['sqlite_witness']['parent_sha256'], anchor.read_bytes(),
    TEST_ANCHOR_KEY,
    expected_anchor_sha256=report['separately_custodialized_capsule_sha256'])
assert state == report['sqlite_witness']
assert report['fork_and_rollback_counterexample']['locally_valid_distinct_forks'] == 2
assert report['fork_and_rollback_counterexample']['valid_prior_history_rejected_after_new_head_published']
assert report['independent_task_ground_truth'] is False
assert report['program_adoptions'] == 0
print('separately pinned-head local fork/rollback comparison PASS')
PY
echo 'v4ak-v4am RESEARCH PASS: valid SQLite fork and rollback detected by separate held head; no real issuer or learner'
