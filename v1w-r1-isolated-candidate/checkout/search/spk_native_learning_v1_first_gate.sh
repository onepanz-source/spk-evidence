#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-native-learning-v1-first.json}"
PARENT="$HOME/workspace/spk-evidence/spk-v5-t17-macro-unknown-actuator.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'NATIVE V1 DENIED: REPORT_ALREADY_EXISTS' >&2; exit 3; }
[[ -f "$PARENT" && ! -L "$PARENT" ]] || { echo 'NATIVE V1 DENIED: T17_FWORK_REPORT_MISSING' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-native-learning-v1-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/6] Frozen SHA source pins + parent T17 SHA + incremental manifest\n'
PYTHONPATH=. python3 - "$PARENT" <<'PY'
import hashlib, json, sys
from pathlib import Path
from spk_native_learning_v1.conformance_v1 import pin_sources
root=Path('.'); manifest=root/'spk_native_learning_v1'/'manifest.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(sys.argv[1])=='9f26022d0ae1361f77b92d9ecb5180dd107696b1909f9f28c23708d123f5c0ac','T17_PARENT_DRIFT'
assert sha(root/'spk_native_learning_v1/reference/t17-fwork.json')==sha(sys.argv[1]),'EMBEDDED_T17_DRIFT'
m=json.loads(manifest.read_text())
assert m['schema']=='spk-native-learning-v1-manifest/first-release'
assert m['frozen_v0e_modified'] is False
assert m['original_v0e_learning'] is False
for rel,expected in m['files'].items():
 p=root/rel
 assert p.is_file() and not p.is_symlink(), 'NEW_FILE_MISSING:'+rel
 assert sha(p)==expected,'NEW_FILE_SHA_DRIFT:'+rel
assert pin_sources('.') and len(m['files'])>=5
print('  Frozen PE + BV byte and loaded-module identities PASS; parent T17 PASS')
PY
printf '[2/6] Bounded native scheduler, real frozen PE and resource modules, 29 tests\n'
PYTHONPATH=. python3 -m pytest -q tests/test_spk_native_learning_v1.py
printf '[3/6] Inherited T17 actuator-learning regressions (not promotion)\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t17_macro_polarity/tests -q
printf '[4/6] Native v1 same-scheduler forward / reverse learning witness\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.conformance_v1 "$TMP/a.json" --root .
printf '[5/6] Independent repeat, bit-exact + machine-readable non-promotion boundary\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.conformance_v1 "$TMP/b.json" --root .
cmp -- "$TMP/a.json" "$TMP/b.json"
PYTHONPATH=. python3 - "$TMP/a.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['schema']=='spk-native-learning-v1-first-same-scheduler-proof/v1'
assert r['status']=='NATIVE_V1_SAME_SCHEDULER_P_MUTATION_DEMONSTRATED'
assert r['native_v1_research_learning'] and not r['original_frozen_BV_learning']
assert r['C_recomputes_on_updated_P_same_scheduler']
for k,first,last in (('12->11',12,11),('11->12',11,12)):
 s=r['proof']['positive_scenarios'][k]
 assert [(x[1],x[2]) for x in s['C_PE_reads']]==[(0,first),(1,last)]
 assert len(s['P_grants'])==1
assert all(r['proof']['negative_controls'].values())
assert r['proof']['frozen_parity']['frozen_PE_forward_and_BV_resource_parity']
print('  SAME-SCHEDULER LEARNING CHAIN PASS; original frozen BV learning ZERO')
PY
printf '[6/6] Frozen source unchanged + publish evidence\n'
PYTHONPATH=. python3 - <<'PY'
from spk_native_learning_v1.conformance_v1 import pin_sources
pin_sources('.')
PY
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/a.json" "$OUT"
sha256sum -- "$OUT"
echo 'SPK NATIVE LEARNING V1 FIRST SAME-SCHEDULER P PROGRAM TRANSITION PASS; FROZEN ORIGINAL BV UNMODIFIED'
