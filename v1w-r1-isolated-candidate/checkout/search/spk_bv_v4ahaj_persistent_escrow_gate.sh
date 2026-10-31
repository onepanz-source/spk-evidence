#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 11 ]]; then
  echo 'Usage: bash search/spk_bv_v4ahaj_persistent_escrow_gate.sh V3TUV.json V4JKL.json V4MNO.json V4PQR.json V4STU.json V4VWX.json V4YZAA.json V4ABAD.json V4AEAG.json NEW-DB.sqlite NEW-REPORT.json' >&2
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

echo '[1/11] v4ah-v4aj restart-persistent escrow, SQLite atomicity, concurrent replay and tamper tests'
python -m unittest discover -s tests -p test_spk_bv_v4ahaj_persistent_escrow.py -v

echo '[2/11] Inherited v4ae-v4ag two correlated reviewer views and disagreement quarantine'
python -m unittest discover -s tests -p test_spk_bv_v4aeag_two_view_adjudication.py -v

echo '[3/11] Inherited v4ab-v4ad dual-attested synthetic task oracle custody'
python -m unittest discover -s tests -p test_spk_bv_v4abad_oracle_custody.py -v

echo '[4/11] Inherited v4y-v4aa external synthetic task objective'
python -m unittest discover -s tests -p test_spk_bv_v4yzaa_task_objective.py -v

echo '[5/11] Inherited v4v-v4x derived candidate authority boundary'
python -m unittest discover -s tests -p test_spk_bv_v4vwx_candidate_authority.py -v

echo '[6/11] Inherited v4s-v4u paid actor consumer'
python -m unittest discover -s tests -p test_spk_bv_v4stu_paid_actor_consumer.py -v

echo '[7/11] Inherited v4p-v4r endogenous actor ACK feedback'
python -m unittest discover -s tests -p test_spk_bv_v4pqr_endogenous_actor_ACK.py -v

echo '[8/11] Inherited v4m-v4o causal native ACK replay'
python -m unittest discover -s tests -p test_spk_bv_v4mno_native_ACK_causal_replay.py -v

echo '[9/11] Frozen native v0e forward/BV dual-scheduler evidence'
python -c 'from search.spk_bv_v0e_live_evidence import capture; r=capture(); assert r["forward_first"]["forward"]["terminal"] and r["feedback_first"]["feedback"]["link_grants"]; print("frozen native v0e smoke PASS")'

echo '[10/11] Create-only source-pinned SQLite escrow and independent bounded observation report'
python -m search.spk_bv_v4ahaj_persistent_escrow \
  --root "$PWD" --v3tuv "$1" --v4aeag "$9" \
  --db "${10}" --out "${11}"

echo '[11/11] Exact observation bytes and independently retained logical head verification'
cmp docs/spk-bv-v4ahaj-persistent-escrow-observation.json "${11}"
python - "${10}" "${11}" <<'PY'
import json
from pathlib import Path
import sys
from spk_bv_research.task_disagreement_fixture_v4aeag import TEST_VIEW_KEYS
from spk_bv_research.task_escrow_store_v4ahaj import DurableEscrow
db, report_path = map(Path, sys.argv[1:])
report = json.loads(report_path.read_bytes())
parent = report['signed_v4aeag_sha256']
head = report['sqlite_logical_witness']['head']
with DurableEscrow.open(db, parent, TEST_VIEW_KEYS, external_head=head) as escrow:
    assert escrow.verify(external_head=head) == report['sqlite_logical_witness']
assert report['program_adoptions'] == 0
assert report['native_learning_implemented'] is False
print('external-head-anchored SQLite review custody PASS')
PY
echo 'v4ah-v4aj RESEARCH PASS: local transactional restart custody; no external task trust or native learning'
