#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
OUT="${1:-$HOME/workspace/spk-evidence/spk-native-learning-v1s-serialized-macro.json}"
PARENT="$HOME/workspace/spk-evidence/spk-native-learning-v1-durable-macro.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'NLV1S REJECT: OUTPUT_ALREADY_EXISTS' >&2;exit 3; }
[[ -f "$PARENT" && ! -L "$PARENT" ]] || { echo 'NLV1S BLOCKED: RUN_V1R_DURABLE_MACRO_GATE_FIRST' >&2;exit 3; }
TMP="$(mktemp -d /tmp/spk-native-v1s-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] Mandatory v1r predecessor full gate evidence, original PE/BV custody and new source pins\n'
PYTHONPATH=. python3 - "$PARENT" <<'PY'
import hashlib,json,sys
from pathlib import Path
from spk_native_learning_v1.conformance_v1 import pin_sources
from spk_native_learning_v1.serialized_conformance_v1s import DURABLE_STATUS
root=Path('.').resolve()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
prior=Path(sys.argv[1]);m=json.loads(prior.read_text())
assert m['status']==DURABLE_STATUS and m['schema']=='spk-native-learning-v1-durable-macro-proof/v1','V1R_PREDECESSOR_NOT_PASS'
assert m['native_v1_intrinsic_learning'] and not m['old_frozen_original_native_learning'],'V1R_SCOPE_DRIFT'
assert m['frozen_source_pins']==pin_sources(root),'ORIGINAL_SOURCE_PINS_DRIFT'
old=json.loads((root/'spk_native_learning_v1/durable_macro_manifest.json').read_text())
assert old['schema']=='spk-native-learning-v1r-durable-macro-manifest/v1'
for rel,h in old['files'].items():
 f=root/rel
 assert f.is_file() and not f.is_symlink() and sha(f)==h,'V1R_FROZEN_VERSIONED_SOURCE_DRIFT:'+rel
new=json.loads((root/'spk_native_learning_v1/serialized_macro_manifest_v1s.json').read_text())
assert new['schema']=='spk-native-learning-v1s-serialized-macro-manifest/v1' and not new['frozen_v0e_modified']
for rel,h in new['files'].items():
 f=root/rel
 assert f.is_file() and not f.is_symlink() and sha(f)==h,'V1S_SOURCE_DRIFT:'+rel
import spk_native_learning_v1.serialized_runtime_v1s as s
import spk_native_learning_v1.durable_runtime_v1 as d
import spk_native_learning_v1.live_learning_scheduler_v1r as r
import spk_architecture_v1.pe_execution_v1b as pe
assert r._compute_local is pe._compute_local,'GENUINE_PE_EXECUTOR_NOT_USED'
assert s.d is d,'DURABLE_RUNTIME_NOT_REUSED'
for module in (s,d,r):
 f=root/(module.__name__.replace('.','/')+'.py')
 assert Path(module.__file__).resolve()==f.resolve(),'SOURCE_MODULE_LOAD_DRIFT'
print('  V1R predecessor + original source + unchanged versioned v1r PASS')
PY
printf '[2/8] New serialized concurrency/replay tests + inherited v1/v1r tests\n'
PYTHONPATH=. python3 -m pytest -q tests/test_spk_native_learning_v1.py tests/test_spk_native_learning_v1_durable.py tests/test_spk_native_learning_v1_serialized.py
printf '[3/8] Inherited scientific and signed-source regressions\n'
for tests in research/spk_v5_t17_macro_polarity/tests research/spk_v5_t16_macro_runtime/tests research/spk_v5_t15_macro_causal_learning/tests research/spk_v5_t14_macro_signed_source/tests; do
 PYTHONPATH=. python3 -m unittest discover -s "$tests" -q
done
printf '[4/8] True PE / actual BV / serialized P continuity run A\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.serialized_conformance_v1s "$TMP/a.json" --root . --parent "$PARENT"
printf '[5/8] Independent genuine source and SQLite replay run B\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.serialized_conformance_v1s "$TMP/b.json" --root . --parent "$PARENT"
cmp -- "$TMP/a.json" "$TMP/b.json"
printf '[6/8] Acceptance, scoped claims, entire-chain P rebinding\n'
PYTHONPATH=. python3 - "$TMP/a.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['status']=='NATIVE_V1S_COOPERATIVE_SERIAL_DURABLE_CHAIN_PASS'
assert r['versioned_v1s_learning'] and not r['original_v0e_learning']
assert r['audited_epochs']==3 and r['continuous_P_versions']==[1,1,2]
assert r['second_execution_new_rows']==0 and len(r['restart_cuts'])==7
assert r['actual_same_scheduler_C_PE_reads'][1][0]==[10,1,11,[11]]
assert r['actual_same_scheduler_C_PE_reads'][2][1]==[30,2,12,[12]]
assert r['frozen_disabled_learning_parity']['frozen_PE_forward_and_BV_resource_parity']
assert r['security_scope']=='COOPERATIVE_WRITERS_ONLY'
print('  SAME SCHEDULER PE READ + SERIALIZED CROSS-PROCESS P PASS, no frozen BV learning')
PY
printf '[7/8] Unmodified frozen PE/BV source custody recheck\n'
PYTHONPATH=. python3 - <<'PY'
from spk_native_learning_v1.conformance_v1 import pin_sources
pin_sources('.')
PY
printf '[8/8] Publish immutable report\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/a.json" "$OUT"
sha256sum -- "$OUT"
echo 'SPK NATIVE LEARNING V1S SERIALIZED DURABLE CAUSAL P CHAIN PASS; COOPERATIVE POSIX LOCK, ORIGINAL BV UNMODIFIED'
