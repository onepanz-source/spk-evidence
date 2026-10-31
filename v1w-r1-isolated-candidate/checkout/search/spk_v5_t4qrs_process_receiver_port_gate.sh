#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t4qrs-process-receiver-port.json}"
ROOT="research/spk_v5_t4qrs"
REF="$ROOT/reference/t4nop-receiver-boundary.json"
[[ ! -e "$OUT" ]] || { echo "T4QRS FAIL CLOSED: OUTPUT_ALREADY_EXISTS $OUT" >&2; exit 3; }
TMP=$(mktemp -d "${TMPDIR:-/tmp}/spk-v5-t4qrs-XXXXXXXX")
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/10] Inherited T4DEF + T4GHI regressions\n'
python3 -m unittest discover -s research/spk_v5_t4def/tests -q
python3 -m unittest discover -s research/spk_v5_t4ghi/tests -q
printf '[2/10] Inherited T4JKL + T4JKLM regressions\n'
python3 -m unittest discover -s research/spk_v5_t4jkl/tests -q
python3 -m unittest discover -s research/spk_v5_t4jkl_fix/tests -q
printf '[3/10] Inherited T4NOP receiver boundary regressions\n'
python3 -m unittest discover -s research/spk_v5_t4nop/tests -q
printf '[4/10] T4QRS strict process-port and adversarial regressions\n'
python3 -m unittest discover -s "$ROOT/tests" -q
printf '[5/10] Source pin, exact report and incremental manifest custody\n'
PYTHONPATH=. python3 - <<'PY'
import json,hashlib
from pathlib import Path
from research.spk_v5_t4qrs import t4qrs as q
from research.spk_v5_t4nop import t4nop
for f,s,n in [
 ('research/spk_v5_t4jkl/manifest.json','spk-v5-t4jkl-incremental-file-custody/v0',5),
 ('research/spk_v5_t4jkl_fix/manifest.json','spk-v5-t4jklm-incremental-file-custody/v0',4),
 ('research/spk_v5_t4nop/manifest.json','spk-v5-t4nop-incremental-file-custody/v0',5),
 ('research/spk_v5_t4qrs/manifest.json','spk-v5-t4qrs-incremental-file-custody/v0',5)]:
    x=json.loads(Path(f).read_bytes())
    assert x['schema']==s and len(x['files'])==n,'MANIFEST_SCHEMA_DRIFT:'+f
    for name,dgst in x['files'].items():
        p=Path(name)
        assert name.startswith(('search/','research/')) and '..' not in p.parts and p.is_file() and not p.is_symlink(),'UNSAFE_MANIFEST_ENTRY:'+name
        assert hashlib.sha256(p.read_bytes()).hexdigest()==dgst,'MANIFEST_PIN_DRIFT:'+name
    print('  verified',f,'files',n)
r=q.load_reference('research/spk_v5_t4qrs/reference/t4nop-receiver-boundary.json')
prior=t4nop.load_reference('research/spk_v5_t4nop/reference/t4jklm-control-flag.json')
pins=t4nop.custody('.',prior)
assert pins==r['N_source_pins'] and len(pins)==12,'FROZEN_SOURCE_SHA_DRIFT'
print('  original 180-row report SHA PASS; 12 source pins PASS')
PY
for attempt in 1 2; do
  WORK="$TMP/run-$attempt"
  mkdir -m 700 "$WORK"
  printf '[%d/10] Independent source scheduler process %d: 180 genuine BV-v0e invocations\n' "$((2*attempt+4))" "$attempt"
  PYTHONPATH=. python3 "$ROOT/t4qrs.py" producer --root . --reference "$REF" --work "$WORK"
  printf '[%d/10] Separate B relay process and A receiver process; 24 commits, 13 attacks\n' "$((2*attempt+5))"
  PYTHONPATH=. python3 "$ROOT/t4qrs.py" relay --root . --reference "$REF" --work "$WORK"
  PYTHONPATH=. python3 "$ROOT/t4qrs.py" receiver --root . --reference "$REF" --work "$WORK"
  PYTHONPATH=. python3 "$ROOT/t4qrs.py" audit --root . --reference "$REF" --work "$WORK" --out "$TMP/run-$attempt-report.json"
done
printf '[10/10] Deterministic report compare; source custody; nonpromotion assertions\n'
cmp -s "$TMP/run-1-report.json" "$TMP/run-2-report.json" || { echo 'T4QRS FAIL CLOSED: REPORT_NONDETERMINISM' >&2; exit 4; }
PYTHONPATH=. python3 - "$TMP/run-1-report.json" <<'PY'
import json,sys
from research.spk_v5_t4qrs import t4qrs as q
r=json.load(open(sys.argv[1]))
assert r['schema']==q.SCHEMA and r['status']==q.STATUS
assert r['reference_sha256']==q.REF_SHA
assert r['producer']['original_BV_calls']==180 and r['producer']['guard_selected']==24
assert r['producer']['semantic_signs']=={'-1':12,'1':12}
assert r['receiver']['committed_count']==24 and r['receiver']['rejected_adversarial_count']==13
assert r['processes_separated']==['C-output-adapter','B-relay','A-receiver']
assert r['verified_result_parity_180'] is True
assert r['host_commissioned_trust_boundary'] is True
assert r['C_neuron_origin_authenticated'] is False
assert r['BV_native_receiver_semantic_receipt'] is False
assert r['native_learning_proven'] is False and r['promotion_allowed'] is False
print('  360 original scheduler calls verified; 48 process-local A commits; 26 adversarial rejections')
print('  NO native C, independent sensor, native BV or learning promotion')
PY
mkdir -p "$(dirname "$OUT")"
cp -n -- "$TMP/run-1-report.json" "$OUT"
sha256sum "$OUT"
echo 'T4QRS EXPERIMENTAL PROCESS RECEIVER PORT PASS; C ADAPTER NOT NATIVE NEURON; NO NATIVE SEMANTIC BV OR LEARNING'
