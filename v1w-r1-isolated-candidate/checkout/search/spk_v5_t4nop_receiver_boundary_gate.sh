#!/usr/bin/env bash
# SPK V5 T4NOP read-only native-receiver boundary research
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-/tmp/spk-v5-t4nop-receiver-boundary.json}"
REPO='research/spk_v5_t4nop'
REF="$REPO/reference/t4jklm-control-flag.json"
[[ ! -e "$OUT" ]] || { echo "T4NOP FAIL CLOSED: OUTPUT_ALREADY_EXISTS: $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-t4nop-XXXXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] T4DEF inherited regressions\n'
python3 -m unittest discover -s research/spk_v5_t4def/tests -q
printf '[2/8] T4GHI inherited regressions\n'
python3 -m unittest discover -s research/spk_v5_t4ghi/tests -q
printf '[3/8] T4JKL original forensic regressions\n'
python3 -m unittest discover -s research/spk_v5_t4jkl/tests -q
printf '[4/8] T4JKLM control-flag hotfix regressions\n'
python3 -m unittest discover -s research/spk_v5_t4jkl_fix/tests -q
printf '[5/8] T4NOP receiver boundary adversarial tests\n'
python3 -m unittest discover -s research/spk_v5_t4nop/tests -q
printf '[6/8] Custody manifests (prior + new) and source pin verification\n'
PYTHONPATH=. python3 - <<'PY'
import hashlib,json
from pathlib import Path
from research.spk_v5_t4nop import t4nop
for path,schema,count in [
    ('research/spk_v5_t4jkl/manifest.json','spk-v5-t4jkl-incremental-file-custody/v0',5),
    ('research/spk_v5_t4jkl_fix/manifest.json','spk-v5-t4jklm-incremental-file-custody/v0',4),
    ('research/spk_v5_t4nop/manifest.json','spk-v5-t4nop-incremental-file-custody/v0',5)]:
    d=json.loads(Path(path).read_text())
    assert d['schema']==schema and len(d['files'])==count,'MANIFEST_STRUCTURE_DRIFT:'+path
    for name,expected in d['files'].items():
        p=Path(name)
        assert name.startswith(('research/','search/')) and '..' not in p.parts and not p.is_symlink() and p.is_file(),'MANIFEST_ENTRY_INVALID:'+name
        assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,'MANIFEST_SHA_DRIFT:'+name
    print('  manifest',path,'PASS',count,'files')
ref=t4nop.load_reference('research/spk_v5_t4nop/reference/t4jklm-control-flag.json')
pins=t4nop.custody('.',ref)
assert len(pins)==12,'SOURCE_PIN_COUNT_DRIFT'
print('  source pins',len(pins),'T4JKLM report SHA PASS; native promotion forbidden')
PY
printf '[7/8] Original frozen BV-v0e producer: 180 source reexecutions; receiver boundary audit\n'
PYTHONPATH=. python3 "$REPO/t4nop.py" --root . --reference "$REF" --out "$TMP/research-report.json"
printf '[8/8] Nonpromotion and evidence integrity\n'
PYTHONPATH=. python3 - "$TMP/research-report.json" <<'PY'
import hashlib,json,sys
r=json.load(open(sys.argv[1]))
assert r['schema']=='spk-v5-t4nop-receiver-boundary/research-v0'
assert r['status']=='RECEIVER_SEMANTIC_BOUNDARY_OBSERVED_BUT_NOT_AUTHENTICATED'
assert r['O_case_count']==180 and r['O_single_source_BV_calls']==180
assert r['O_sign_observations']==72 and r['O_emission_triples']==48
assert r['O_research_guard_count']==24 and r['P_native_semantic_credit_accepted']==0
assert r['P_trusted_native_authenticator_available'] is False
assert r['native_receiver_semantic_receipt_proven'] is False
assert r['native_learning_proven'] is False and r['promotion_allowed'] is False
assert len(r['O_rows'])==180 and all(x['native_receiver_semantic_credit'] is False for x in r['O_rows'])
assert r['O_cross_sign_receiver_shape']['dual_sign_receiver_schema_groups']>0
assert r['P_untrusted_receipt_probe']['native_credit'] is False
print('  180 exact source SHA parity; zero native semantic receipts; zero learning promotion')
PY
mkdir -p "$(dirname "$OUT")"
cp -- "$TMP/research-report.json" "$OUT"
sha256sum "$OUT"
echo "T4NOP RECEIVER SEMANTIC BOUNDARY RESEARCH PASS; NO NATIVE BV OR LEARNING"
