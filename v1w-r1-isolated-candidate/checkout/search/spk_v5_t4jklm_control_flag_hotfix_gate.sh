#!/usr/bin/env bash
# SPK V5 T4JKL-M control/forward flag separation, additive research-only hotfix.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-/tmp/spk-v5-t4jklm-control-flag.json}"
PY='research/spk_v5_t4jkl_fix/t4jkl_fix.py'
REF='research/spk_v5_t4jkl/reference/t4ghi-one-pass-sign.json'
[[ ! -e "$OUT" ]] || { echo "T4JKL-M FAIL CLOSED: OUTPUT_ALREADY_EXISTS: $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-t4jklm-XXXXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] T4DEF inherited tests\n'
python3 -m unittest discover -s research/spk_v5_t4def/tests -q
printf '[2/8] T4GHI inherited tests\n'
python3 -m unittest discover -s research/spk_v5_t4ghi/tests -q
printf '[3/8] Original T4JKL forensic tests (unchanged)\n'
python3 -m unittest discover -s research/spk_v5_t4jkl/tests -q
printf '[4/8] T4JKL-M decision/forward/reverse separation and adversarial tests\n'
python3 -m unittest discover -s research/spk_v5_t4jkl_fix/tests -q
printf '[5/8] Chain-of-custody: old + new package manifests; source pins; source recipe controls\n'
PYTHONPATH=. python3 - <<'PY'
import json,hashlib,inspect
from pathlib import Path
from research.spk_v5_t4jkl_fix import t4jkl_fix as m

def check_manifest(path,expected_schema,expected_len):
    manifest=json.loads(Path(path).read_text())
    assert manifest['schema']==expected_schema and len(manifest['files'])==expected_len, 'MANIFEST_SCHEMA_OR_LENGTH_INVALID'
    for name,digest in manifest['files'].items():
        p=Path(name)
        assert '..' not in p.parts and not p.is_absolute() and p.is_file() and not p.is_symlink(), 'INVALID_MANIFEST_MEMBER:'+name
        assert hashlib.sha256(p.read_bytes()).hexdigest()==digest, 'MANIFEST_SHA_DRIFT:'+name
    print('  verified manifest',path,'files',len(manifest['files']))

check_manifest('research/spk_v5_t4jkl/manifest.json','spk-v5-t4jkl-incremental-file-custody/v0',5)
check_manifest('research/spk_v5_t4jkl_fix/manifest.json','spk-v5-t4jklm-incremental-file-custody/v0',4)
ref=m.reference('research/spk_v5_t4jkl/reference/t4ghi-one-pass-sign.json')
pins=m.custody('.')
assert len(pins)==11, 'SOURCE_PINS_COUNT_DRIFT'
checks=m.offline_analysis(ref)
assert checks['research_guard_eligible_count']==24 and checks['emission_triple_count']==48
for key in ('application_send_decision_enabled_false','application_action_forward_enabled_false','application_reverse_enabled_false'):
    assert checks['input_recipe_control_disabled_counts'][key]==36,'RECIPE_PARTITION_INVALID:'+key
print('  custody pins',len(pins),'cases',len(ref['H_rows']),'guard-only candidates 24; no native promotion')
PY
printf '[6/8] Independent producer process 1: 180 source BV cases, corrected input controls\n'
PYTHONPATH=. python3 "$PY" --root . --reference "$REF" --out "$TMP/run1.json"
printf '[7/8] Independent producer process 2: 180 source BV cases, byte-exact deterministic replay\n'
PYTHONPATH=. python3 "$PY" --root . --reference "$REF" --out "$TMP/run2.json"
cmp -s "$TMP/run1.json" "$TMP/run2.json" || { echo 'T4JKL-M FAIL CLOSED: NONDETERMINISTIC_REPORT' >&2; exit 3; }
PYTHONPATH=. python3 - "$TMP/run1.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['schema']=='spk-v5-t4jklm-control-separation/research-v0'
assert r['status']=='SAME_SOURCE_SIGN_WITH_SEPARATE_DECISION_FORWARD_CONTROLS_RESEARCH_ONLY'
assert r['L_same_source_reexecution_count']==180
assert r['L_source_result_parity_180'] is True and r['L_recipe_flag_comparisons_180'] is True
assert r['K_offline']['research_guard_eligible_count']==24
assert r['native_receiver_semantic_receipt_proven'] is False
assert r['native_learning_proven'] is False and r['promotion_allowed'] is False
assert r['authenticated_sensor_authority_proven'] is False
assert all(row['native_semantic_receipt_proven'] is False for row in r['L_rows'])
print('  180 x 2 original source executions verified; no native semantic/learning promotion')
PY
printf '[8/8] Persist sealed research report and SHA256\n'
mkdir -p "$(dirname "$OUT")"
cp -- "$TMP/run1.json" "$OUT"
sha256sum "$OUT"
echo 'T4JKL-M CONTROL FLAG HOTFIX RESEARCH PASS; NO NATIVE SEMANTIC BV OR LEARNING'
