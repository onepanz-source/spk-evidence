#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t4wxy-c-context-reference.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo "T4WXY FAIL CLOSED: OUTPUT_EXISTS $OUT" >&2; exit 3; }
TMP=$(mktemp -d "${TMPDIR:-/tmp}/spk-v5-t4wxy-gate-XXXXXXXX")
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/7] Inherited T4DEF / GHI / JKL / JKLM / NOP / QRS / TUV regressions\n'
for n in t4def t4ghi t4jkl t4jkl_fix t4nop t4qrs t4tuv; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${n}/tests" -q
done
printf '[2/7] Experimental C-context emitter / relay / receiver / host-forgery tests\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t4wxy/tests -q
printf '[3/7] Package manifest and original T4TUV source pins\n'
PYTHONPATH=. python3 - <<'PY'
import hashlib,json
from pathlib import Path
from research.spk_v5_t4wxy import t4wxy as t
from research.spk_v5_t4tuv import t4tuv as prev
root=Path('research/spk_v5_t4wxy')
manifest=json.loads((root/'manifest.json').read_text())
assert manifest['schema']=='spk-v5-t4wxy-incremental-file-custody/v0'
assert len(manifest['files'])==5
for path,sha in manifest['files'].items():
 p=Path(path)
 assert not p.is_absolute() and '..' not in p.parts and path.startswith(('research/','search/'))
 assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==sha,path
r=t.reference(root/'reference/t4tuv-host-authority-counterexample.json')
ref,ghi,qrs=prev.references('.')
assert r['source_pins']==ref['N_source_pins']==qrs['source_pins']
assert r['T_cached_source_invocations_this_run']==0
print('  additive manifest',len(manifest['files']),'PASS, TUV original SHA PASS, 12 source pins PASS')
PY
for i in 1 2; do
 printf '[%d/7] Independent 3-process reference port round %s (NO original BV calls)\n' "$((i+3))" "$i"
 PYTHONPATH=. python3 research/spk_v5_t4wxy/t4wxy.py run --root . \
   --reference research/spk_v5_t4wxy/reference/t4tuv-host-authority-counterexample.json \
   --out "$TMP/report-$i.json"
done
printf '[6/7] Determinism and mandatory host-forgery witness\n'
cmp -s "$TMP/report-1.json" "$TMP/report-2.json" || { echo 'T4WXY FAIL CLOSED: REPORT_NONDETERMINISTIC' >&2; exit 4; }
PYTHONPATH=. python3 - "$TMP/report-1.json" <<'PY'
import json,sys
from research.spk_v5_t4wxy import t4wxy as t
x=json.load(open(sys.argv[1]))
assert x['status']==t.STATUS and x['schema']==t.SCHEMA
assert x['W_original_BV_scheduler_calls']==0 and x['W_reference_C_compute_steps']==24
assert x['X_receiver_process_commits']==24 and x['X_positive']==12 and x['X_negative']==12
assert x['X_adversarial_rejections']==14
assert x['Y_host_can_forge_even_with_reference_C_context']['host_outside_C_can_forge'] is True
assert x['Y_host_can_forge_even_with_reference_C_context']['host_fake_A_accepts']==1
assert x['Y_native_neuron_identity_verified'] is False and x['Y_native_BV_semantic_receipts']==0
assert x['Y_native_learning'] is False and x['promotion_allowed'] is False
print('  PASS: C-context computes & emits; host forgery STILL POSSIBLE; no native promotion')
PY
printf '[7/7] Seal deterministic research-only report\n'
mkdir -p "$(dirname "$OUT")"
cp -- "$TMP/report-1.json" "$OUT"
sha256sum "$OUT"
echo 'T4WXY EXPERIMENTAL C-CONTEXT REFERENCE PASS; HOST STILL CONTROLS AUTHORITY; NO NATIVE C BV OR LEARNING'
