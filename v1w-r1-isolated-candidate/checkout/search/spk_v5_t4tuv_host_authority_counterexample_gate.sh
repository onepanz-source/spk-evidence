#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t4tuv-host-authority-counterexample.json}"
ROOT="research/spk_v5_t4tuv"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo "T4TUV FAIL CLOSED: OUTPUT_ALREADY_EXISTS $OUT" >&2; exit 3; }
TMP=$(mktemp -d "${TMPDIR:-/tmp}/spk-v5-t4tuv-XXXXXXXX")
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] Inherited T4DEF/GHI/JKL/JKLM/NOP/QRS regressions\n'
for n in t4def t4ghi t4jkl t4jkl_fix t4nop t4qrs; do
  PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${n}/tests" -q
done
printf '[2/8] T4TUV cached-issuer falsification and untrusted-origin negative tests\n'
PYTHONPATH=. python3 -m unittest discover -s "$ROOT/tests" -q
printf '[3/8] Incremental manifests, archived evidence, and original 12 source pins\n'
PYTHONPATH=. python3 - <<'PY'
import json,hashlib
from pathlib import Path
from research.spk_v5_t4tuv import t4tuv as t
from research.spk_v5_t4nop import t4nop
specs=(
('research/spk_v5_t4jkl/manifest.json','spk-v5-t4jkl-incremental-file-custody/v0',5),
('research/spk_v5_t4jkl_fix/manifest.json','spk-v5-t4jklm-incremental-file-custody/v0',4),
('research/spk_v5_t4nop/manifest.json','spk-v5-t4nop-incremental-file-custody/v0',5),
('research/spk_v5_t4qrs/manifest.json','spk-v5-t4qrs-incremental-file-custody/v0',5),
('research/spk_v5_t4tuv/manifest.json','spk-v5-t4tuv-incremental-file-custody/v0',5))
for fn,schema,expected in specs:
    manifest=json.loads(Path(fn).read_bytes())
    assert manifest['schema']==schema and len(manifest['files'])==expected,'MANIFEST_SCHEMA_MISMATCH:'+fn
    for path,sha in manifest['files'].items():
        p=Path(path)
        assert not p.is_absolute() and '..' not in p.parts and path.startswith(('research/','search/')),'UNSAFE_MANIFEST_ENTRY:'+path
        assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==sha,'MANIFEST_SHA_DRIFT:'+path
    print('  manifest',fn,'PASS',expected,'files')
ref,ghi,old=t.references('.')
pins=t4nop.custody('.',t4nop.load_reference('research/spk_v5_t4nop/reference/t4jklm-control-flag.json'))
assert len(pins)==12 and pins==ref['N_source_pins']==old['source_pins'],'SOURCE_CUSTODY_FAILED'
print('  exact T4GHI, T4NOP and T4QRS report pins PASS; original 12 source SHA pins PASS')
PY
for attempt in 1 2; do
  WORK="$TMP/run-$attempt"
  mkdir -m 700 "$WORK"
  printf '[%d/8] Independent cached-only producer + B relay, A receiver, original T4QRS audit: iteration %d\n' "$((attempt+3))" "$attempt"
  # Deliberately NO t4ghi.source_once / BV producer call. This is a counterexample.
  PYTHONPATH=. python3 "$ROOT/t4tuv.py" cached --root . --work "$WORK"
  PYTHONPATH=. python3 "$ROOT/t4tuv.py" relay --root . --work "$WORK"
  PYTHONPATH=. python3 "$ROOT/t4tuv.py" receiver --root . --work "$WORK"
  PYTHONPATH=. python3 "$ROOT/t4tuv.py" audit --root . --work "$WORK" --out "$TMP/report-$attempt.json"
done
printf '[6/8] Independent process reproducibility and exact archival T4QRS forgery counterexample\n'
cmp -s "$TMP/report-1.json" "$TMP/report-2.json" || { echo 'T4TUV FAIL CLOSED: COUNTEREXAMPLE_NONDETERMINISM' >&2; exit 4; }
PYTHONPATH=. python3 - "$TMP/report-1.json" "$TMP/run-1/counterfeit-qrs-report.json" <<'PY'
import sys
from research.spk_v5_t4qrs import t4qrs as q
from research.spk_v5_t4tuv import t4tuv as t
r=q.read(sys.argv[1]);fake=sys.argv[2]
assert r['schema']==t.SCHEMA and r['status']==t.STATUS,'T4TUV_SCHEMA_OR_STATUS_DRIFT'
assert r['T_cached_source_invocations_this_run']==0,'FALSE_CREDIT_FOR_SOURCE_EXECUTION'
assert r['T_reconstructed_QRS_sha256']==r['T_original_QRS_sha256']==q.sha(fake)==t.QRS_REPORT_SHA,'T4QRS_COUNTEREXAMPLE_SHA_DRIFT'
assert r['T_same_A_ledger_sha256']=='f5d762cf9607ceb1ca6ba286472d0597535949a67e651b8047503c2940fd30a2','LEDGER_SHA_DRIFT'
assert r['T_A_process_accepted_cached_packets']==24 and r['T_A_process_adversarial_rejections']==13
assert r['U_natively_verified_semantic_receipts']==0 and r['U_native_source_authentication_available'] is False
assert r['native_receiver_semantic_receipt_proven'] is False and r['native_learning_proven'] is False
assert r['promotion_allowed'] is False and len(r['source_pins'])==12
print('  ARCHIVED HOST-ENROLLED data recreate original QRS report byte-for-byte; real source calls 0')
print('  This falsifies native-origin inference from A ledger, NOT the original 360 verified scheduler calls')
PY
printf '[7/8] Final nonpromotion and original-report immutability\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t4tuv import t4tuv as t
from pathlib import Path
r,g,q=t.references('.')
assert q['promotion_allowed'] is False and q['C_neuron_origin_authenticated'] is False
assert len(g['H_rows'])==180
assert not any(row['native_receiver_semantic_credit'] for row in r['O_rows'])
print('  Source-output historic evidence remains research-only; no native issuer, receiver or learning')
PY
printf '[8/8] Persist sealed T4TUV result\n'
mkdir -p "$(dirname "$OUT")"
cp -- "$TMP/report-1.json" "$OUT"
sha256sum "$OUT"
echo 'T4TUV HOST-ISSUER AUTHORITY COUNTEREXAMPLE PASS; NO NATIVE C SEMANTIC BV OR LEARNING'
