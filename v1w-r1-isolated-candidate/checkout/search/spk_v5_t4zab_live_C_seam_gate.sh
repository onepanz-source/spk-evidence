#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t4zab-live-C-seam.json}"
SOURCES="$(dirname "$OUT")/spk-v5-t4zab-frozen-seam-sources.tar.gz"
[[ ! -e "$OUT" && ! -L "$OUT" && ! -e "$SOURCES" && ! -L "$SOURCES" ]] || { echo 'T4ZAB FAIL CLOSED: OUTPUT_EXISTS' >&2; exit 3; }
TMP=$(mktemp -d "${TMPDIR:-/tmp}/spk-v5-t4zab-XXXXXXXX")
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/7] Inherited T4DEF → T4WXY regression tests\n'
for n in t4def t4ghi t4jkl t4jkl_fix t4nop t4qrs t4tuv t4wxy; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${n}/tests" -q
done
printf '[2/7] New PE C-step observation adversarial tests\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t4zab/tests -q
printf '[3/7] New additive file manifest and WXY source pins\n'
PYTHONPATH=. python3 - <<'PY2'
import hashlib,json
from pathlib import Path
from research.spk_v5_t4zab import t4zab as t
base=Path('research/spk_v5_t4zab')
manifest=json.loads((base/'manifest.json').read_bytes())
assert manifest['schema']=='spk-v5-t4zab-file-custody/v0'
assert len(manifest['files'])==5
for rel,pin in manifest['files'].items():
 p=Path(rel)
 assert not p.is_symlink() and p.is_file() and '..' not in p.parts and hashlib.sha256(p.read_bytes()).hexdigest()==pin, rel
wxy=t.wxy_ref(base/'reference/t4wxy-c-context-reference.json')
assert t.verify_origins(Path('.'),wxy)==wxy['source_pins']
print('  5 new files and 12 original source pins verified')
PY2
for i in 1 2; do
 printf '[%d/7] Independent original BV-v0e 180-case producer, live C PE observer %s\n' "$((i+3))" "$i"
 PYTHONPATH=. python3 research/spk_v5_t4zab/t4zab.py run --root . \
    --reference research/spk_v5_t4zab/reference/t4wxy-c-context-reference.json \
    --out "$TMP/report-$i.json"
done
printf '[6/7] Exact report parity, nonpromotion, and immutable source copies\n'
cmp -s "$TMP/report-1.json" "$TMP/report-2.json" || { echo 'T4ZAB FAIL CLOSED: NONDETERMINISTIC_SOURCE_OBSERVATION' >&2;exit 4; }
PYTHONPATH=. python3 - "$TMP/report-1.json" <<'PY3'
from pathlib import Path
import json,sys
from research.spk_v5_t4zab import t4zab as t
x=json.loads(Path(sys.argv[1]).read_text())
assert x['status']==t.STATUS and x['original_BV_source_invocations']==180
assert x['genuine_C_compute_observation_rows']==180 and x['signed_source_results']==72
assert x['host_callback_can_forge_C_claim'] is True
assert x['original_modules_unchanged'] is True
assert x['C_execution_owned_emission_proven'] is False
assert x['C_origin_authenticated'] is False
assert x['receiver_native_semantic_receipts']==0
assert x['native_learning_proven'] is False and x['promotion_allowed'] is False
assert all(r['C_compute_call_count']>0 and r['native_C_packet_origin_verified'] is False for r in x['rows'])
print('  360 original frozen scheduler executions; live PE observer remains host owned; no promotion')
PY3
mkdir -p "$(dirname "$OUT")"
PYTHONPATH=. python3 research/spk_v5_t4zab/t4zab.py bundle --root . --out "$SOURCES"
cp -- "$TMP/report-1.json" "$OUT"
sha256sum "$OUT" "$SOURCES"
echo 'T4ZAB LIVE PE C STEP SEAM PASS; HOST HOOK NOT NATIVE C, NO NATIVE BV OR LEARNING'
