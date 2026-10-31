#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 14 ]]; then
  echo 'Usage: bash search/spk_bv_v4anap_research_closure_gate.sh V3TUV.json V4JKL.json V4MNO.json V4PQR.json V4STU.json V4VWX.json V4YZAA.json V4ABAD.json V4AEAG.json V4AHAJ.sqlite V4AHAJ.json V4AKAM-ANCHOR.json V4AKAM-REPORT.json NEW-CLOSURE.json' >&2
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
export SPK_V4AHAJ_DB="${10}"
export SPK_V4AHAJ_REPORT="${11}"
export SPK_V4AKAM_ANCHOR="${12}"
export SPK_V4AKAM_REPORT="${13}"

echo '[1/13] v4an-v4ap research boundary, source custody, false-closure and tampering tests'
python -m unittest discover -s tests -p test_spk_bv_v4anap_research_closure.py -v

echo '[2/13] Inherited v4ak-v4am divergent valid fork/rollback tests'
python -m unittest discover -s tests -p test_spk_bv_v4akam_external_anchor.py -v

echo '[3/13] Inherited v4ah-v4aj durable escrow tests'
python -m unittest discover -s tests -p test_spk_bv_v4ahaj_persistent_escrow.py -v

echo '[4/13] Inherited v4ae-v4ag correlated two-view tests'
python -m unittest discover -s tests -p test_spk_bv_v4aeag_two_view_adjudication.py -v

echo '[5/13] Inherited v4ab-v4ad synthetic oracle custody tests'
python -m unittest discover -s tests -p test_spk_bv_v4abad_oracle_custody.py -v

echo '[6/13] Inherited v4y-v4aa task objective tests'
python -m unittest discover -s tests -p test_spk_bv_v4yzaa_task_objective.py -v

echo '[7/13] Inherited v4v-v4x candidate-authority tests'
python -m unittest discover -s tests -p test_spk_bv_v4vwx_candidate_authority.py -v

echo '[8/13] Inherited v4s-v4u paid actor tests'
python -m unittest discover -s tests -p test_spk_bv_v4stu_paid_actor_consumer.py -v

echo '[9/13] Inherited v4p-v4r endogenous actor ACK tests'
python -m unittest discover -s tests -p test_spk_bv_v4pqr_endogenous_actor_ACK.py -v

echo '[10/13] Inherited v4m-v4o native causal ACK tests'
python -m unittest discover -s tests -p test_spk_bv_v4mno_native_ACK_causal_replay.py -v

echo '[11/13] Frozen native v0e independent two-scheduler smoke'
python -c 'from search.spk_bv_v0e_live_evidence import capture; r=capture(); assert r["forward_first"]["forward"]["terminal"] and r["feedback_first"]["feedback"]["link_grants"]; print("frozen native v0e PASS")'

echo '[12/13] Create-only exact-source research closure record'
python -m search.spk_bv_v4anap_research_closure \
  --root "$PWD" --v4aeag "${9}" --v4ahaj "${11}" --db "${10}" \
  --anchor "${12}" --v4akam "${13}" --out "${14}"

echo '[13/13] Byte-exact release observation, no external certification'
cmp docs/spk-bv-v4anap-research-closure-observation.json "${14}"
python - "${14}" <<'PY'
from pathlib import Path
import json
import sys
r = json.loads(Path(sys.argv[1]).read_bytes())
assert r['status'] == 'BOUNDED_RESEARCH_PROTOCOL_CLOSED_EXTERNAL_VALIDATION_PENDING'
assert r['evidence_counts']['inherited_tests'] == 199
assert len(r['research_acceptance']) == 8
assert all(r['research_acceptance'].values())
assert not any(r['unmet_independent_validation'].values())
assert not r['claim_policy']['native_self_learning_implemented']
assert r['evidence_counts']['native_program_adoptions'] == 0
print('RESEARCH BOUNDARY CLOSED: 218 unit tests; live external task truth and trust root NOT established')
PY
