#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
OUT="${1:-$HOME/workspace/spk-evidence/spk-native-learning-v1-durable-macro.json}"
PARENT="$HOME/workspace/spk-evidence/spk-native-learning-v1-first.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'NATIVE V1R DENIED: REPORT_ALREADY_EXISTS' >&2; exit 3; }
[[ -f "$PARENT" && ! -L "$PARENT" ]] || { echo 'NATIVE V1R DENIED: FIRST_NATIVE_V1_FWORK_REPORT_MISSING' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-native-learning-v1r-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/7] Parent FWORK report + frozen SPK SHA + new source manifest\n'
PYTHONPATH=. python3 - "$PARENT" <<'PY'
from pathlib import Path
import hashlib,json,sys
from spk_native_learning_v1.conformance_v1 import pin_sources
from spk_native_learning_v1.durable_conformance_v1 import PARENT_SHA
root=Path('.').resolve(); sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(Path(sys.argv[1]))==PARENT_SHA,'PARENT_NATIVE_V1_FWORK_SHA_DRIFT'
p=root/'spk_native_learning_v1/reference/native-v1-first-fwork.json'
assert sha(p)==PARENT_SHA,'EMBEDDED_NATIVE_V1_PARENT_DRIFT'
pins=pin_sources(root)
manifest=root/'spk_native_learning_v1/durable_macro_manifest.json'
m=json.loads(manifest.read_text())
assert m['schema']=='spk-native-learning-v1r-durable-macro-manifest/v1'
assert m['original_frozen_BV_modified'] is False
assert m['original_frozen_BV_natively_learns'] is False
for rel,h in m['files'].items():
 f=root/rel
 assert f.is_file() and not f.is_symlink(),'MISSING_OR_SYMLINK:'+rel
 assert sha(f)==h,'SOURCE_SHA_DRIFT:'+rel
import spk_native_learning_v1.live_learning_scheduler_v1r as scheduler
import spk_native_learning_v1.durable_runtime_v1 as durable
import spk_native_learning_v1.durable_conformance_v1 as conformance
for module in (scheduler,durable,conformance):
 f=root/(module.__name__.replace('.','/')+'.py')
 assert Path(module.__file__).resolve()==f.resolve(),'LOADED_NEW_MODULE_DRIFT:'+module.__name__
import spk_architecture_v1.pe_execution_v1b as original_pe
import spk_architecture_v1.causal_memory_v1c as original_mem
assert scheduler._compute_local is original_pe._compute_local and scheduler._admit is original_pe._admit, 'NEW_V1R_FROZEN_PE_BINDING_DRIFT'
assert scheduler._valid_memory is original_mem._valid_memory and scheduler._reservation is original_mem._reservation, 'NEW_V1R_FROZEN_MEMORY_BINDING_DRIFT'
assert len(pins)==3 and len(m['files'])>=6
print('  Frozen source and import identity PASS; predecessor and archive pins PASS')
PY
printf '[2/7] Native first milestone + 42 restart/P continuity tests\n'
PYTHONPATH=. python3 -m pytest -q tests/test_spk_native_learning_v1.py tests/test_spk_native_learning_v1_durable.py
printf '[3/7] Inherited T17/T16/T15/T14 scientific/protocol regressions\n'
for tests in research/spk_v5_t17_macro_polarity/tests research/spk_v5_t16_macro_runtime/tests research/spk_v5_t15_macro_causal_learning/tests research/spk_v5_t14_macro_signed_source/tests; do
  PYTHONPATH=. python3 -m unittest discover -s "$tests" -q
done
printf '[4/7] Genuine SPK v1 durable recovery, actual PE + BV + inherited P, run A\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.durable_conformance_v1 "$TMP/a.json" --root .
printf '[5/7] Independently recreated SQLite ledger and source replay, run B\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.durable_conformance_v1 "$TMP/b.json" --root .
cmp -- "$TMP/a.json" "$TMP/b.json"
printf '[6/7] Full causal acceptance boundary, not frozen-v0e learning\n'
PYTHONPATH=. python3 - "$TMP/a.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['status']=='NATIVE_V1_DURABLE_P_INHERITANCE_AND_CAUSAL_REPLAY_PASS'
assert r['native_v1_intrinsic_learning'] and not r['old_frozen_original_native_learning']
assert len(r['crash_cut_recovery'])==7
assert all(x['P_version']==1 for x in r['crash_cut_recovery'])
e=r['cross_epoch_P']['epochs']
assert [(x['id'],x['final_P']['version'],x['final_P']['choice']) for x in e]==[(0,1,11),(1,1,11),(2,2,12)]
assert e[1]['C_PE_reads'][0]==[10,1,11,[11]]
assert e[2]['C_PE_reads'][1]==[30,2,12,[12]]
assert r['frozen_v0e_disabled_learning_parity']['frozen_PE_forward_and_BV_resource_parity']
assert r['clean']['C_PE_reads']==[[10,0,12,[12]],[30,1,11,[11]]]
assert r['durability']=='SQLITE_TICK_WAL_PLUS_VERIFIED_GENESIS_REPLAY'
print('  DURABLE REPLAY + CROSS-EPOCH INTRINSIC P PASS; FROZEN ORIGINAL LEARNING ZERO')
PY
printf '[7/7] Original SPK SHA unchanged; publish immutable report\n'
PYTHONPATH=. python3 - <<'PY'
from spk_native_learning_v1.conformance_v1 import pin_sources
pin_sources('.')
PY
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/a.json" "$OUT"
sha256sum -- "$OUT"
echo 'SPK NATIVE LEARNING V1 DURABLE CROSS-EPOCH P REPLAY MACRO PASS; ORIGINAL BV-V0E UNMODIFIED'
