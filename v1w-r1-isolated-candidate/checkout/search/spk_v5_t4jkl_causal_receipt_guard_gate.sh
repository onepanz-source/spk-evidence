#!/usr/bin/env bash
# Incremental research milestone, never modifies frozen architecture/learning.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-/tmp/spk-v5-t4jkl-causal-receipt-guard.json}"
REF="research/spk_v5_t4jkl/reference/t4ghi-one-pass-sign.json"
PY="research/spk_v5_t4jkl/t4jkl.py"
[[ ! -e "$OUT" ]] || { echo "T4JKL FAIL CLOSED: OUTPUT_ALREADY_EXISTS: $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-t4jkl-XXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/7] T4DEF inherited regressions\n'
python3 -m unittest discover -s research/spk_v5_t4def/tests -v
printf '[2/7] T4GHI inherited regressions\n'
python3 -m unittest discover -s research/spk_v5_t4ghi/tests -v
printf '[3/7] T4JKL new causal/action/receiver adversarial regressions\n'
python3 -m unittest discover -s research/spk_v5_t4jkl/tests -v
printf '[4/7] Validate archive manifest, source pins, exact prior report, negative-control partition\n'
PYTHONPATH=. python3 - <<'PY'
import json,hashlib
from pathlib import Path
mp=Path('research/spk_v5_t4jkl/manifest.json')
manifest=json.loads(mp.read_text())
assert manifest['schema']=='spk-v5-t4jkl-incremental-file-custody/v0'
assert len(manifest['files'])==5
for name,expected in manifest['files'].items():
    path=Path(name)
    assert '..' not in path.parts and not path.is_absolute()
    assert path.is_file() and not path.is_symlink()
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected, 'MILESTONE_FILE_SHA_DRIFT:'+name
print('incremental milestone manifest verified:',len(manifest['files']),'files')
PY
PYTHONPATH=. python3 - "$REF" <<'PY'
import sys
from research.spk_v5_t4jkl import t4jkl as m
from pathlib import Path
r=m.reference(sys.argv[1]); pins=m.custody('.')
p=m.offline_analysis(r)
assert p['research_guard_eligible_count']==24 and p['emission_triple_count']==48
assert p['classification_counts']['APPLICATION_FORWARD_GUARD_BLOCK']==24
print('source pins',len(pins),'single-source candidates 72, temporal triples 48, application-guard research 24; none native')
PY
printf '[5/7] Independent-process rerun 1: 180 original BV source cases\n'
PYTHONPATH=. python3 "$PY" --root . --reference "$REF" --out "$TMP/run1.json"
printf '[6/7] Independent-process rerun 2: 180 source cases; byte-exact parity\n'
PYTHONPATH=. python3 "$PY" --root . --reference "$REF" --out "$TMP/run2.json"
cmp -s "$TMP/run1.json" "$TMP/run2.json" || { echo 'T4JKL FAIL CLOSED: INDEPENDENT_PROCESS_NONDETERMINISM' >&2; exit 3; }
python3 - "$TMP/run1.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['status']=='SAME_SOURCE_SIGN_WITH_APPLICATION_CUSTODY_GUARD_RESEARCH_ONLY'
assert r['L_same_source_reexecution_count']==180 and r['L_source_result_parity_180'] is True
assert r['K_offline']['research_guard_eligible_count']==24
assert r['K_offline']['classification_counts']['APPLICATION_FORWARD_GUARD_BLOCK']==24
assert r['native_receiver_semantic_receipt_proven'] is False
assert r['native_learning_proven'] is False and r['promotion_allowed'] is False
assert r['authenticated_sensor_authority_proven'] is False
assert all(row['native_semantic_receipt_proven'] is False for row in r['L_rows'])
print('single-BV-per-case 180/180 parity on each of 2 producer reruns; nonpromotion asserted')
PY
printf '[7/7] Persist report and report SHA256\n'
mkdir -p "$(dirname "$OUT")"
cp -- "$TMP/run1.json" "$OUT"
sha256sum "$OUT"
echo 'T4JKL CAUSAL RECEIPT GUARD RESEARCH PASS; NO RECEIVER-AUTHENTICATED SEMANTIC BV OR LEARNING'
