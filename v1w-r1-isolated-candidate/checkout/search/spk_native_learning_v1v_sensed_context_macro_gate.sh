#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
OUT="${1:-$HOME/workspace/spk-evidence/spk-native-learning-v1v-pe-sensed-context.json}"
PARENT="$HOME/workspace/spk-evidence/spk-native-learning-v1u-contextual-macro.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'V1V REJECT: OUTPUT_ALREADY_EXISTS' >&2; exit 3; }
[[ -f "$PARENT" && ! -L "$PARENT" ]] || { echo 'V1V BLOCKED: V1U_PASS_REPORT_REQUIRED' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-native-v1v-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] Exact v1u PASS, original frozen PE/BV pins, prior and v1v file manifests\n'
PYTHONPATH=. python3 - "$PARENT" <<'PY'
import json,sys,hashlib
from pathlib import Path
from spk_native_learning_v1.generalized_case_v1t import pin_sources
from spk_native_learning_v1.sensed_context_conformance_v1v import PARENT_SHA,PARENT_STATUS
from spk_native_learning_v1.sensed_context_v1v import _source_check
root=Path('.').resolve();sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
f=Path(sys.argv[1]);prior=json.loads(f.read_text());pins=pin_sources(root)
assert sha(f)==PARENT_SHA and prior['status']==PARENT_STATUS and prior['native_v1_research_learning'],'V1U_PARENT_MISMATCH'
assert not prior['frozen_original_BV_learning'] and prior['original_frozen_pins']==pins,'ORIGINAL_SOURCE_DRIFT'
assert _source_check(root)==pins,'ORIGINAL_PE_IMPORT_BYPASS'
for rel in ('spk_native_learning_v1/durable_macro_manifest.json',
            'spk_native_learning_v1/serialized_macro_manifest_v1s.json',
            'spk_native_learning_v1/generalized_manifest_v1t.json',
            'spk_native_learning_v1/contextual_manifest_v1u.json',
            'spk_native_learning_v1/sensed_context_manifest_v1v.json'):
    file=root/rel
    assert file.is_file() and not file.is_symlink(),'MANIFEST_MISSING:'+rel
    obj=json.loads(file.read_text())
    assert all(obj.get(key) is not True for key in ('frozen_components_modified',
       'original_frozen_BV_modified','frozen_v0e_modified')),'MUTATED_FROZEN:'+rel
    for name,h in obj['files'].items():
        source=root/name
        assert source.is_file() and not source.is_symlink() and sha(source)==h,'MANIFEST_SOURCE_DRIFT:'+name
latest=json.loads((root/'spk_native_learning_v1/sensed_context_manifest_v1v.json').read_text())
assert latest['schema']=='spk-native-learning-v1v-pe-sensed-context-manifest/v1' and latest['parent']=='v1u'
from spk_native_learning_v1 import sensed_context_v1v as mod,sensed_context_conformance_v1v as conf
for name,module in [('sensed_context_v1v',mod),('sensed_context_conformance_v1v',conf)]:
    assert Path(module.__file__).resolve()==root/'spk_native_learning_v1'/(name+'.py'),'SENSED_SOURCE_IMPORT_WRONG:'+name
print('  original frozen provenance, 5 manifests, v1u parent PASS')
PY
printf '[2/8] New v1v original-PE selector, P binding, crash and adversarial tests\n'
PYTHONPATH=. python3 -m pytest -q tests/test_spk_native_learning_v1_sensed_context.py
printf '[3/8] Native-v1u/v1t/v1s/v1r/v1 inherited PE/BV and durability regressions\n'
PYTHONPATH=. python3 -m pytest -q tests/test_spk_native_learning_v1_contextual.py \
 tests/test_spk_native_learning_v1_generalized.py \
 tests/test_spk_native_learning_v1_serialized.py \
 tests/test_spk_native_learning_v1_durable.py \
 tests/test_spk_native_learning_v1.py
printf '[4/8] T14–T17 inherited signed-source/scientific regressions\n'
for dir in research/spk_v5_t17_macro_polarity/tests research/spk_v5_t16_macro_runtime/tests research/spk_v5_t15_macro_causal_learning/tests research/spk_v5_t14_macro_signed_source/tests; do
 PYTHONPATH=. python3 -m unittest discover -s "$dir" -q
done
printf '[5/8] Full-checkout original PE and BV conformance report A\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.sensed_context_conformance_v1v "$TMP/a.json" --root . --parent "$PARENT"
printf '[6/8] Independent full-checkout conformance report B, exact bytes\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.sensed_context_conformance_v1v "$TMP/b.json" --root . --parent "$PARENT"
cmp -- "$TMP/a.json" "$TMP/b.json"
printf '[7/8] Strict scientific scope, original-source custody and no v0e promotion\n'
PYTHONPATH=. python3 - "$TMP/a.json" <<'PY'
import sys,json
from spk_native_learning_v1.generalized_case_v1t import pin_sources
x=json.load(open(sys.argv[1]))
assert x['status']=='V1V_PE_SENSED_CONTEXT_P_RECALL_PASS'
assert x['frozen_source_pins']==pin_sources('.') and x['real_original_PE_classifier']
assert x['episodes']==5 and x['persistent_tick_rows']==325 and x['second_run_new_tick_rows']==0
assert x['derived_contexts']==['ctx0','ctx1','ctx0','ctx1','ctx0']
assert x['derived_context_versions']==[2,1,2,1,3] and x['P_grants_by_epoch']==[2,1,0,0,1]
assert x['signature_to_internal_context']=={'s71':'ctx0','s72':'ctx1'}
assert x['noise_equivalent_classes'] and x['reversed_observation_order_retains_association']
assert len(x['restart_cuts'])==7 and x['tamper_denied']
assert set(x['negative_sensor_rejections'])=={'mixed','ambiguous','missing','duplicate'}
assert x['versioned_v1v_research_learning'] and not x['host_passes_context_label']
assert not x['frozen_original_BV_learning'] and not x['promotion_allowed']
print('  PE SENSED CONTEXT → P RECALL VERIFIED; FROZEN BV-v0e UNMODIFIED')
PY
printf '[8/8] Publish immutable evidence report\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/a.json" "$OUT"
sha256sum -- "$OUT"
echo 'SPK NATIVE LEARNING V1V ORIGINAL-PE SENSED CONTEXT P RECALL PASS; HOST RAW CUES, ORIGINAL BV UNMODIFIED'
