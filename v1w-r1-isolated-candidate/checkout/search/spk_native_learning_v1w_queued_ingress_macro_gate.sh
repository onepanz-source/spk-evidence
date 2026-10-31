#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
OUT="${1:-$HOME/workspace/spk-evidence/spk-native-learning-v1w-queued-ingress.json}"
PARENT="$HOME/workspace/spk-evidence/spk-native-learning-v1v-pe-sensed-context.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'V1W REJECT: OUTPUT_ALREADY_EXISTS' >&2; exit 3; }
[[ -f "$PARENT" && ! -L "$PARENT" ]] || { echo 'V1W BLOCKED: PREDECESSOR V1V REQUIRED' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-native-v1w-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] Exact v1v PASS, pinned original PE/BV, prior + v1w manifests\n'
PYTHONPATH=. python3 - "$PARENT" <<'PY'
import hashlib,json,sys
from pathlib import Path
from spk_native_learning_v1 import ingress_conformance_v1w as conf
from spk_native_learning_v1.generalized_case_v1t import pin_sources
from spk_native_learning_v1 import sensed_context_v1v as sensed
root=Path.cwd();parent=Path(sys.argv[1]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(parent)==conf.PARENT_SHA,'V1V_PARENT_SHA_DRIFT'
r=json.loads(parent.read_text());original=pin_sources(root)
assert r['status']==conf.PARENT_STATUS and r['real_original_PE_classifier'],'V1V_NOT_PASS'
assert not r['frozen_original_BV_learning'] and r['frozen_source_pins']==original,'V1V_ORIGINAL_DRIFT'
assert sensed._source_check(root)==original,'ORIGINAL_PE_NOT_LOADED'
for rel in ('spk_native_learning_v1/durable_macro_manifest.json',
            'spk_native_learning_v1/serialized_macro_manifest_v1s.json',
            'spk_native_learning_v1/generalized_manifest_v1t.json',
            'spk_native_learning_v1/contextual_manifest_v1u.json',
            'spk_native_learning_v1/sensed_context_manifest_v1v.json',
            'spk_native_learning_v1/ingress_manifest_v1w.json'):
    p=root/rel
    assert p.is_file() and not p.is_symlink(),'MANIFEST_MISSING:'+rel
    m=json.loads(p.read_text())
    assert not any(m.get(k) is True for k in ('frozen_components_modified','original_frozen_BV_modified','frozen_v0e_modified')),'FROZEN_MUTATION:'+rel
    for path,h in m['files'].items():
        f=root/path
        assert f.is_file() and not f.is_symlink() and sha(f)==h,'SOURCE_PIN_DRIFT:'+path
manifest=json.loads((root/'spk_native_learning_v1/ingress_manifest_v1w.json').read_text())
assert manifest['schema']=='spk-native-learning-v1w-queued-ingress-manifest/v1'
assert manifest['parent_v1v_SHA256']==conf.PARENT_SHA
from spk_native_learning_v1 import ingress_scheduler_v1w as mod
assert Path(mod.__file__).resolve()==root/'spk_native_learning_v1/ingress_scheduler_v1w.py','V1W_SOURCE_MODULE_SUBSTITUTION'
print('  V1V exact parent, original PE/BV provenance, 6 source manifests PASS')
PY
printf '[2/8] New v1w queued original PE admission, replay, crash and adversarial tests\n'
PYTHONPATH=. python3 -m pytest -q tests/test_spk_native_learning_v1_queued_ingress.py
printf '[3/8] Inherited v1v/v1u/v1t/v1s/v1r/first PE BV P regression suites\n'
PYTHONPATH=. python3 -m pytest -q \
 tests/test_spk_native_learning_v1_sensed_context.py \
 tests/test_spk_native_learning_v1_contextual.py \
 tests/test_spk_native_learning_v1_generalized.py \
 tests/test_spk_native_learning_v1_serialized.py \
 tests/test_spk_native_learning_v1_durable.py \
 tests/test_spk_native_learning_v1.py
printf '[4/8] T14-T17 source/scientific inherited regressions\n'
for folder in research/spk_v5_t17_macro_polarity/tests \
 research/spk_v5_t16_macro_runtime/tests \
 research/spk_v5_t15_macro_causal_learning/tests \
 research/spk_v5_t14_macro_signed_source/tests; do
 [[ -d "$folder" ]] || { echo "V1W BLOCKED: MISSING_INHERITED_SUITE $folder" >&2; exit 3; }
 PYTHONPATH=. python3 -m unittest discover -s "$folder" -q
done
printf '[5/8] Original-source full PE/BV/P v1w experiment A\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.ingress_conformance_v1w "$TMP/a.json" --root . --parent "$PARENT"
printf '[6/8] Independent full PE/BV/P experiment B; exact byte comparison\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.ingress_conformance_v1w "$TMP/b.json" --root . --parent "$PARENT"
cmp -- "$TMP/a.json" "$TMP/b.json"
printf '[7/8] Functional causal criteria and explicit native v1 / frozen v0e boundary\n'
PYTHONPATH=. python3 - "$TMP/a.json" <<'PY'
import json,sys
from spk_native_learning_v1.generalized_case_v1t import pin_sources
r=json.load(open(sys.argv[1]))
assert r['status']=='V1W_QUEUED_PE_INGRESS_GATES_CONTEXTUAL_NATIVE_V1_P_PASS'
assert r['frozen_source_pins']==pin_sources('.')
assert r['parent_v1v_SHA256']=='172b2a1c72a526ca3cc49d9792d4d765b606f7d4b34644b4b47248a264a69e4b'
assert r['episodes']==5 and r['committed_BV_tick_rows']==325 and r['staged_ingress_event_rows']==25
assert r['P_versions']==[2,1,2,1,3] and r['P_grants']==[2,1,0,0,1]
assert r['context_ids']==['ctx0','ctx1','ctx0','ctx1','ctx0']
assert r['observed_PE_signatures']==['s71','s72','s71','s72','s71']
assert r['second_run_new_BV_ticks']==0 and r['legacy_context_api_fenced_on_v1w_db']
assert r['original_PE_classification_at_ingress_consumption'] and not r['classification_on_queue']
assert r['reverse_context_order_binding']=={'s72':'ctx0','s71':'ctx1'}
assert len(r['stage_recovery'])==4 and len(r['BV_recovery'])==7
assert set(r['negative_inputs_denied'])=={'mixed','ambiguous','duplicate','unknown'}
assert r['research_v1_native_learning'] and not r['frozen_BV_v0e_learning']
assert r['original_frozen_components_unchanged'] and not r['promotion_allowed']
assert r['frozen_source_pins']==pin_sources('.')
print('  CONTEXT FROM QUEUED PE → NATIVE V1 SAME-SCHEDULER BV P VERIFIED; FROZEN V0E NO LEARNING')
PY
printf '[8/8] Publish immutable verified v1w report\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/a.json" "$OUT"
sha256sum -- "$OUT"
echo 'SPK NATIVE LEARNING V1W QUEUED PE INGRESS AND CONTEXTUAL BV P REBIND PASS; FROZEN ORIGINAL BV UNMODIFIED'
