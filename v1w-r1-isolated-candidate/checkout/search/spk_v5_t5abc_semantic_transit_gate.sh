#!/usr/bin/env bash
# T5ABC cumulative frozen-output-parity fork experiment, additive only.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t5abc-semantic-transit.json}"
[[ ! -e "$OUT" ]] || { echo "T5ABC FAIL CLOSED: OUTPUT_ALREADY_EXISTS: $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-t5abc-gate-XXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/7] Verify incremental manifest and no frozen-source modification\n'
PYTHONPATH=. python3 - <<'PY'
import hashlib,json
from pathlib import Path
p=Path('research/spk_v5_t5abc')
m=json.loads((p/'manifest.json').read_bytes())
assert m['schema']=='spk-v5-t5abc-additive-source-manifest/v0'
assert len(m['files'])==6
for filename,sha in sorted(m['files'].items()):
 q=Path(filename)
 assert q.is_file() and not q.is_symlink()
 assert hashlib.sha256(q.read_bytes()).hexdigest()==sha,('SHA_DRIFT',filename)
from research.spk_v5_t5abc.t5abc import custodial_fork_check
print('T5ABC SHA PINS',custodial_fork_check(Path('.')))
PY
printf '[2/7] New offline fork synthetic parity and hostile-input tests\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t5abc/tests -v
printf '[3/7] Inherited topology regression tests (T4ZABC)\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t4zabc/tests -q
printf '[4/7] Independent research fork process 1: 180 genuine PE-bound BV source cases\n'
PYTHONPATH=. python3 research/spk_v5_t5abc/t5abc.py --root . --out "$TMP/one.json"
printf '[5/7] Independent research fork process 2: deterministic independent replay\n'
PYTHONPATH=. python3 research/spk_v5_t5abc/t5abc.py --root . --out "$TMP/two.json"
printf '[6/7] Byte-exact replay / source parity / nonpromotion checks\n'
cmp -- "$TMP/one.json" "$TMP/two.json"
python3 - "$TMP/one.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
assert x['status']=='IN_SCHEDULER_PE_OUTPUT_BOUND_BV_TO_A_RESEARCH_NOT_AUTHENTICATED'
assert x['fork_BV_calls']==180 and x['original_BV_calls_in_this_run']==0
assert x['in_scheduler_C_issuances']==x['A_received_sign_messages']==72
assert x['C_B_A_semantic_feedback_hops']==144
assert x['application_guard_research_candidates_not_native_credit']==24
assert x['byte_exact_frozen_output_parity'] is True
assert all(x[k] is False for k in ('native_C_identity_authenticated','native_receiver_semantic_credit_proven','native_learning_proven','promotion_allowed'))
assert x['host_can_forge_runtime'] is True
assert len(x['rows'])==180 and sum(r['A_receipt_count'] for r in x['rows'])==72
assert all(r['native_credit'] is False for r in x['rows'])
print('T5ABC 360 FORK RUNS; 180/180 EACH FROZEN SHA PARITY; 72 A SIGN RECEIPTS EACH; NATIVE CREDIT ZERO')
PY
printf '[7/7] Persist sealed research-only report\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/one.json" "$OUT"
sha256sum -- "$OUT"
echo "T5ABC IN-SCHEDULER C-OUTPUT SEMANTIC TRANSIT RESEARCH PASS; HOST CAN FORGE; NO NATIVE BV OR LEARNING"
