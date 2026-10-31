#!/usr/bin/env bash
# SPK V5 T5DEF: additive PE-scope descriptor experiment; native claims forbidden.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t5def-pe-scope-issuer.json}"
[[ ! -e "$OUT" ]] || { echo "T5DEF FAIL CLOSED: OUTPUT_ALREADY_EXISTS: $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-v5-t5def-XXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] New additive manifest, prior T5ABC manifest, source pins and exact old report\n'
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
import hashlib,json
for path,schema,minimum in [
 ('research/spk_v5_t5abc/manifest.json','spk-v5-t5abc-additive-source-manifest/v0',6),
 ('research/spk_v5_t5def/manifest.json','spk-v5-t5def-additive-source-manifest/v0',7)]:
    p=Path(path)
    if not p.is_file():raise SystemExit('T5DEF FAIL CLOSED: MANIFEST_MISSING')
    v=json.loads(p.read_bytes())
    if v['schema']!=schema or len(v['files'])!=minimum:raise SystemExit('T5DEF FAIL CLOSED: MANIFEST_SCHEMA_OR_COUNT')
    for fn,sha in sorted(v['files'].items()):
        f=Path(fn)
        if not f.is_file() or f.is_symlink() or hashlib.sha256(f.read_bytes()).hexdigest()!=sha:
            raise SystemExit('T5DEF FAIL CLOSED: MANIFEST_SHA_DRIFT: '+fn)
    print('  manifest',path,'PASS files',len(v['files']))
from research.spk_v5_t5def import t5def
from research.spk_v5_t5abc import t5abc
print('  source',t5def.check_custody(Path('.')))
v=t5abc.read_pinned(Path('research/spk_v5_t5def/reference/t5abc-semantic-transit.json'),
    t5def.REFERENCE_SHA,'T5ABC_REFERENCE')
assert v['fork_BV_calls']==180 and v['host_can_forge_runtime'] is True
print('  T5ABC reference report pin PASS')
PY
printf '[2/8] PE issuer adversarial unit and host-rebind counterexample tests\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t5def/tests -q
printf '[3/8] Inherited original T5ABC parity and attack regressions\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t5abc/tests -q
printf '[4/8] Inherited BV/PE topology regression (T4ZABC)\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t4zabc/tests -q
printf '[5/8] Independent fork process 1: 180 real PE calls + PE-scope issuance\n'
PYTHONPATH=. python3 research/spk_v5_t5def/t5def.py --root . --out "$TMP/one.json"
printf '[6/8] Independent fork process 2: full replay and mandatory host-forgery witness\n'
PYTHONPATH=. python3 research/spk_v5_t5def/t5def.py --root . --out "$TMP/two.json"
printf '[7/8] Deterministic byte parity, nonpromotion and archival reference assertions\n'
cmp -- "$TMP/one.json" "$TMP/two.json"
python3 - "$TMP/one.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
assert x['status']=='PE_SCOPE_ISSUER_TRANSPORT_PARITY_HOST_REBINDABLE_NOT_NATIVE'
assert x['experimental_fork_cases']==180 and x['frozen_source_calls']==0
assert (x['PE_scope_compute_steps'],x['C_PE_compute_steps'],x['PE_scope_sign_issuances'],
        x['A_sign_receipts'],x['semantic_hops'],x['research_guard_only_cases'])==(1002,312,72,72,144,24)
assert x['all_180_frozen_and_T5ABC_port_sha_parity'] is True
w=x['host_rebind_forgery_witness']
assert w['C_PE_compute_calls_in_replay']==0 and w['C_cached_substitutions']>0
assert w['same_scheduler_and_semantic_result_bytes'] is True
assert w['native_origin_authentication_falsified'] is True
assert x['host_can_forge_runtime'] is True
assert all(x[k] is False for k in ('native_neuron_origin_authenticated','native_semantic_BV_proven',
                                  'native_learning_proven','promotion_allowed'))
assert len(x['rows'])==180 and all(r['native_credit'] is False for r in x['rows'])
print('T5DEF: PE-SCOPE PARITY 180/180; HOST-REBOUND C COMPUTE SKIPPED; AUTHENTICATION NOT PROVEN')
PY
printf '[8/8] Persist research-only report with SHA256\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/one.json" "$OUT"
sha256sum -- "$OUT"
echo 'T5DEF PE SCOPE ISSUER EXPERIMENT PASS; HOST STILL CAN FORGE; NO NATIVE BV OR LEARNING'
