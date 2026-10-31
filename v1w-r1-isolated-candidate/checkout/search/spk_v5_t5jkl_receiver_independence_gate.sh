#!/usr/bin/env bash
# T5JKL: research-only source receipt vs independent A judgment; no runtime mutation.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t5jkl-receiver-independence.json}"
[[ ! -e "$OUT" ]] || { echo "T5JKL FAIL CLOSED: OUTPUT_ALREADY_EXISTS $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-v5-t5jkl-XXXXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] All incremental source manifests and pinned historic T5GHI/T4GHI evidence\n'
PYTHONPATH=. python3 - <<'PY'
import json,hashlib
from pathlib import Path
from research.spk_v5_t5jkl import t5jkl
for name,schema,n in (
    ('research/spk_v5_t5abc/manifest.json','spk-v5-t5abc-additive-source-manifest/v0',6),
    ('research/spk_v5_t5def/manifest.json','spk-v5-t5def-additive-source-manifest/v0',7),
    ('research/spk_v5_t5ghi/manifest.json','spk-v5-t5ghi-additive-manifest/research-v0',10),
    ('research/spk_v5_t5jkl/manifest.json','spk-v5-t5jkl-additive-manifest/research-v0',7)):
    p=Path(name)
    if not p.is_file() or p.is_symlink():raise SystemExit('T5JKL FAIL CLOSED: MANIFEST_MISSING '+name)
    m=json.loads(p.read_bytes())
    if m['schema']!=schema or len(m['files'])!=n:raise SystemExit('T5JKL FAIL CLOSED: MANIFEST_SCHEMA '+name)
    for f,v in m['files'].items():
        q=Path(f)
        if not q.is_file() or q.is_symlink() or hashlib.sha256(q.read_bytes()).hexdigest()!=v:
            raise SystemExit('T5JKL FAIL CLOSED: MANIFEST_SHA_DRIFT '+f)
    print('  manifest',name,'PASS',n)
print('  original 12 source SHA pins',t5jkl.custody('.',True)['original_source_pins'],'PASS')
PY
printf '[2/8] New research independence and adversarial classification tests\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t5jkl/tests -q
printf '[3/8] Inherited T5GHI and T5DEF regressions\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t5ghi/tests -q
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t5def/tests -q
printf '[4/8] Inherited T5ABC / T4ZABC regressions\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t5abc/tests -q
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t4zabc/tests -q
printf '[5/8] Independent source-pinned offline cross-plane audit 1 (NO new PE/scheduler calls)\n'
PYTHONPATH=. python3 -m research.spk_v5_t5jkl.t5jkl --root . --out "$TMP/one.json"
printf '[6/8] Independent source-pinned offline cross-plane audit 2\n'
PYTHONPATH=. python3 -m research.spk_v5_t5jkl.t5jkl --root . --out "$TMP/two.json"
printf '[7/8] Deterministic parity, no-independent-judgment and mandatory nonpromotion\n'
cmp -- "$TMP/one.json" "$TMP/two.json"
python3 - "$TMP/one.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1]));q=v['classification_counts']
assert v['schema']=='spk-v5-t5jkl-receiver-independence-audit/research-v0'
assert v['status']=='FRESH_RECEIPT_NOT_INDEPENDENT_A_JUDGMENT_OR_NATIVE_CREDIT'
assert (v['cases'],v['new_original_scheduler_calls'],v['new_PE_compute_calls'])==(180,0,0)
assert q=={'NO_SIGN_RECEIVED':108,'FRESH_RECEIPT_GUARD_CANDIDATE':24,
 'FRESH_RECEIPT_WITH_SOURCE_FAULT':48,'fork_receipt_without_source_forward_emission_chain':24,
 'fresh_received':72,'research_guard_candidates':24,'source_chain_observed':48}
assert v['all_180_source_sha_parity'] is True and v['A_independent_goal_observations']==0
assert v['A_independent_judgments_authenticated']==0 and v['native_BV_credit']==0
assert v['native_learning'] is False and v['native_C_authenticated'] is False
assert v['promotion_allowed'] is False and v['privileged_host_cached_rebind_succeeds'] is True
assert v['source_pins']['original_source_pins']==12
assert len(v['rows'])==180 and all(r['native_semantic_BV_credit'] is False and
  r['A_independent_judgment_authenticated'] is False for r in v['rows'])
print('T5JKL: 72 FRESH RECEIPTS, 24 RESEARCH GUARDS, 0 INDEPENDENT A JUDGMENTS, 0 NATIVE CREDIT')
PY
printf '[8/8] Seal report and print hash\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/one.json" "$OUT"
sha256sum -- "$OUT"
echo 'T5JKL RECEIVER INDEPENDENCE & SOURCE-PROVENANCE CROSS-PLANE AUDIT PASS; NO NATIVE BV OR LEARNING'
