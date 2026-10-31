#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
OUT="${1:-$HOME/workspace/spk-evidence/spk-native-learning-v1t-three-choice-macro.json}"
PARENT="$HOME/workspace/spk-evidence/spk-native-learning-v1s-serialized-macro.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'V1T REJECT: OUTPUT_ALREADY_EXISTS' >&2; exit 3; }
[[ -f "$PARENT" && ! -L "$PARENT" ]] || { echo 'V1T BLOCKED: V1S_PREDECESSOR_REPORT_REQUIRED' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-native-v1t-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] V1S full successful predecessor, original frozen source pins and versioned source integrity\n'
PYTHONPATH=. python3 - "$PARENT" <<'PY'
import hashlib,json,sys
from pathlib import Path
from spk_native_learning_v1.generalized_case_v1t import pin_sources
from spk_native_learning_v1.generalized_conformance_v1t import PARENT_SHA,PARENT_STATUS
root=Path('.').resolve()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
parent=Path(sys.argv[1]);j=json.loads(parent.read_text())
assert sha(parent)==PARENT_SHA and j['status']==PARENT_STATUS,'V1S_PARENT_INVALID_OR_CHANGED'
assert j['versioned_v1s_learning'] and not j['original_v0e_learning'],'V1S_SCOPE_DRIFT'
assert j['original_frozen_pins']==pin_sources(root),'FROZEN_SOURCE_PIN_DRIFT'
for rel in ('spk_native_learning_v1/durable_macro_manifest.json','spk_native_learning_v1/serialized_macro_manifest_v1s.json',
            'spk_native_learning_v1/generalized_manifest_v1t.json'):
    f=root/rel
    assert f.is_file() and not f.is_symlink(), 'MANIFEST_MISSING:'+rel
    m=json.loads(f.read_text())
    for artifact,expected in m['files'].items():
        p=root/artifact
        assert p.is_file() and not p.is_symlink() and sha(p)==expected, 'SOURCE_DRIFT:'+artifact
new=json.loads((root/'spk_native_learning_v1/generalized_manifest_v1t.json').read_text())
assert new['schema']=='spk-native-learning-v1t-generalized-macro-manifest/v1' and not new['frozen_components_modified']
import spk_native_learning_v1.generalized_scheduler_v1t as v
import spk_architecture_v1.pe_execution_v1b as pe
assert v._compute_local is pe._compute_local and v._admit is pe._admit,'GENUINE_PE_FUNCTION_NOT_USED'
for name in ('generalized_scheduler_v1t','generalized_case_v1t','generalized_durable_v1t','generalized_serial_v1t','generalized_conformance_v1t'):
    module=__import__('spk_native_learning_v1.'+name,fromlist=[name])
    assert Path(module.__file__).resolve()==(root/'spk_native_learning_v1'/(name+'.py')).resolve(),'MODULE_LOADED_FROM_WRONG_SOURCE:'+name
print('  frozen originals, v1r, v1s and v1t source custody PASS')
PY
printf '[2/8] New v1t nine-pair, persistence, concurrent-writer and adversarial tests\n'
PYTHONPATH=. python3 -m pytest -q tests/test_spk_native_learning_v1_generalized.py
printf '[3/8] Inherited native scheduler + durability + serialized concurrency regressions\n'
PYTHONPATH=. python3 -m pytest -q tests/test_spk_native_learning_v1.py tests/test_spk_native_learning_v1_durable.py tests/test_spk_native_learning_v1_serialized.py
printf '[4/8] Inherited T15/T16/T17 scientific and T14 signed-source regressions\n'
for dir in research/spk_v5_t17_macro_polarity/tests research/spk_v5_t16_macro_runtime/tests research/spk_v5_t15_macro_causal_learning/tests research/spk_v5_t14_macro_signed_source/tests; do
  PYTHONPATH=. python3 -m unittest discover -s "$dir" -q
done
printf '[5/8] Full v1t PE / live-BV / durable all-nine-case proof, run A\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.generalized_conformance_v1t "$TMP/a.json" --root . --parent "$PARENT"
printf '[6/8] Independent full proof run B and byte-exact comparison\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.generalized_conformance_v1t "$TMP/b.json" --root . --parent "$PARENT"
cmp -- "$TMP/a.json" "$TMP/b.json"
printf '[7/8] Scoped release acceptance + frozen original source custody recheck\n'
PYTHONPATH=. python3 - "$TMP/a.json" <<'PY'
import json,sys
from spk_native_learning_v1.generalized_case_v1t import pin_sources
j=json.load(open(sys.argv[1]))
assert j['status']=='NATIVE_V1T_THREE_CHOICE_SAME_SCHEDULER_DURABLE_LEARNING_PASS'
assert j['candidate_choices']==[11,12,15] and len(j['three_choice_pairs'])==9
assert j['versioned_v1t_learning'] and not j['frozen_v0e_learning']
assert j['frozen_BV_disabled_learning_parity']['frozen_3choice_PE_BV_parity']
assert j['durable_three_choice_chain']['versions']==[2,2,3]
assert j['durable_three_choice_chain']['second_run_new_ticks']==0
assert len(j['durable_three_choice_chain']['crash_recovery'])==7
assert j['frozen_original_source_pins']==pin_sources('.')
print('  V1T THREE-CHOICE ACTUAL PE/BV + SERIAL CAUSAL P PASS; NO FROZEN BV LEARNING')
PY
printf '[8/8] Publish immutable scoped report\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/a.json" "$OUT"
sha256sum -- "$OUT"
echo 'SPK NATIVE LEARNING V1T THREE-CHOICE P REBIND AND SERIAL DURABILITY PASS; ORIGINAL BV UNMODIFIED'
