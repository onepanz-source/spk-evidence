#!/usr/bin/env bash
# SPK V5 T5GHI: research-only receiver-issued fresh challenge, NOT native C attestation.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t5ghi-receiver-freshness.json}"
[[ ! -e "$OUT" ]] || { echo "T5GHI FAIL CLOSED: OUTPUT_ALREADY_EXISTS: $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-v5-t5ghi-XXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/9] Old T5DEF and T5ABC manifests, new incremental manifest; source custody and archived report\n'
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
import hashlib,json
checks=[('research/spk_v5_t5abc/manifest.json','spk-v5-t5abc-additive-source-manifest/v0',6),
        ('research/spk_v5_t5def/manifest.json','spk-v5-t5def-additive-source-manifest/v0',7),
        ('research/spk_v5_t5ghi/manifest.json','spk-v5-t5ghi-additive-manifest/research-v0',10)]
for path,schema,n in checks:
    p=Path(path)
    if not p.is_file() or p.is_symlink():raise SystemExit('T5GHI FAIL CLOSED: MANIFEST_MISSING '+path)
    v=json.loads(p.read_bytes())
    if v['schema']!=schema or len(v['files'])!=n:raise SystemExit('T5GHI FAIL CLOSED: MANIFEST_INVALID '+path)
    for f,sha in sorted(v['files'].items()):
        q=Path(f)
        if not q.is_file() or q.is_symlink() or hashlib.sha256(q.read_bytes()).hexdigest()!=sha:
            raise SystemExit('T5GHI FAIL CLOSED: MANIFEST_SHA_DRIFT '+f)
    print('  manifest',path,'PASS',n,'files')
from research.spk_v5_t5ghi import t5ghi
from research.spk_v5_t5abc import t5abc
print('  source pins',t5ghi.custody(Path('.')))
r=t5abc.read_pinned(Path('research/spk_v5_t5ghi/reference/t5def-pe-scope-issuer.json'),
                    t5ghi.REF_SHA,'T5DEF_REFERENCE')
assert r['experimental_fork_cases']==180 and r['PE_scope_sign_issuances']==72
assert r['host_can_forge_runtime'] is True and r['promotion_allowed'] is False
print('  exact T5DEF PASS report SHA and no-native constraints PASS')
PY
printf '[2/9] Receiver challenge protocol, PE binding, hostile host-rebind unit tests\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t5ghi/tests -q
printf '[3/9] Inherited T5DEF PE-scope and host-falsification regressions\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t5def/tests -q
printf '[4/9] Inherited T5ABC semantic transit and T4ZABC BV/PE topology regressions\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t5abc/tests -q
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t4zabc/tests -q
printf '[5/9] Independent process 1: 180 fork executions; independent A challenge process; 72 fresh receives\n'
PYTHONPATH=. python3 research/spk_v5_t5ghi/t5ghi.py --root . --out "$TMP/one.json"
printf '[6/9] Independent process 2: fresh independent random challenges; 180 fork executions\n'
PYTHONPATH=. python3 research/spk_v5_t5ghi/t5ghi.py --root . --out "$TMP/two.json"
printf '[7/9] Byte-identical public reports despite independent random A-owned nonces\n'
cmp -- "$TMP/one.json" "$TMP/two.json"
printf '[8/9] Nonpromotion; mandatory privileged host forgery; rejection counts; old parity\n'
python3 - "$TMP/one.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
assert x['schema']=='spk-v5-t5ghi-receiver-freshness-pe-scope/research-v0'
assert x['status']=='RECEIVER_FRESHNESS_REPLAY_BLOCKED_PRIVILEGED_HOST_CAN_REBIND_NOT_NATIVE'
assert (x['fork_cases'],x['original_frozen_BV_calls'],x['PE_steps'],x['C_steps'],x['C_fresh_issuances'])==(180,0,1002,312,72)
assert x['A_receiver_process_stats']=={'issued':180,'accepted':72,'expired':108,'rejected':4}
assert x['freshness_attack_rejections']=={'altered_digest':1,'altered_sign':1,'replay':1,'wrong_case':1}
assert x['A_nonce_uniqueness_checked'] is True and x['ephemeral_nonces_omitted_from_report'] is True
assert x['all_180_source_and_T5DEF_port_sha_parity'] is True
w=x['host_rebind_forgery_witness']
assert w['C_new_PE_computations']==0 and w['cached_C_results_rebound']>0
assert w['fresh_challenge_accepted_by_A'] is True and w['native_origin_attestation_falsified'] is True
assert x['host_can_forge_runtime'] is True
assert all(x[k] is False for k in ('native_C_authenticated','native_BV_credit','native_learning','promotion_allowed'))
assert len(x['rows'])==180 and sum(r['A_fresh_accept'] for r in x['rows'])==72
assert all(r['native_credit'] is False for r in x['rows'])
print('T5GHI: A CHALLENGE-REPLAY PROTECTION PASS; HOST REBIND FORGERY CONFIRMED; NO NATIVE C ATTESTATION')
PY
printf '[9/9] Seal deterministic research-only report and SHA256\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/one.json" "$OUT"
sha256sum -- "$OUT"
echo 'T5GHI RECEIVER-OWNED FRESHNESS RESEARCH PASS; PRIVILEGED HOST STILL CAN FORGE; NO NATIVE BV OR LEARNING'
