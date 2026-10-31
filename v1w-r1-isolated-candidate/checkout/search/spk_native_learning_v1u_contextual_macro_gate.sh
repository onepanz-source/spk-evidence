#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
OUT="${1:-$HOME/workspace/spk-evidence/spk-native-learning-v1u-contextual-macro.json}"
PARENT="$HOME/workspace/spk-evidence/spk-native-learning-v1t-three-choice-macro.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'V1U REJECT: OUTPUT_ALREADY_EXISTS' >&2; exit 3; }
[[ -f "$PARENT" && ! -L "$PARENT" ]] || { echo 'V1U BLOCKED: V1T_REPORT_REQUIRED' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-native-v1u-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] V1T predecessor, exact original PE/BV pins and all versioned manifests\n'
PYTHONPATH=. python3 - "$PARENT" <<'PY'
import hashlib,json,sys
from pathlib import Path
from spk_native_learning_v1.contextual_conformance_v1u import PARENT_SHA,PARENT_STATUS
from spk_native_learning_v1.generalized_case_v1t import pin_sources
from spk_native_learning_v1 import generalized_scheduler_v1t as runtime
from spk_architecture_v1 import pe_execution_v1b as original
root=Path('.').resolve();f=Path(sys.argv[1]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
j=json.loads(f.read_text())
assert sha(f)==PARENT_SHA and j['status']==PARENT_STATUS and j['versioned_v1t_learning'] and not j['frozen_v0e_learning'],'PREDECESSOR_INVALID'
assert j['frozen_original_source_pins']==pin_sources(root),'FROZEN_SOURCE_INVALID'
assert runtime._compute_local is original._compute_local and runtime._admit is original._admit,'NOT_ORIGINAL_PE'
for rel in ('spk_native_learning_v1/durable_macro_manifest.json',
            'spk_native_learning_v1/serialized_macro_manifest_v1s.json',
            'spk_native_learning_v1/generalized_manifest_v1t.json',
            'spk_native_learning_v1/contextual_manifest_v1u.json'):
    path=root/rel
    assert path.is_file() and not path.is_symlink(),'MANIFEST_MISSING:'+rel
    manifest=json.loads(path.read_text())
    for name,pin in manifest['files'].items():
        src=root/name
        assert src.is_file() and not src.is_symlink() and sha(src)==pin,'SOURCE_DRIFT:'+name
new=json.loads((root/'spk_native_learning_v1/contextual_manifest_v1u.json').read_text())
assert new['schema']=='spk-native-learning-v1u-contextual-P-bank-macro-manifest/v1' and not new['frozen_components_modified']
for name in ('contextual_durable_v1u','contextual_serial_v1u','contextual_conformance_v1u'):
    module=__import__('spk_native_learning_v1.'+name,fromlist=[name])
    assert Path(module.__file__).resolve()==root/'spk_native_learning_v1'/(name+'.py'),'WRONG_IMPORT_SOURCE:'+name
print('  pinned frozen original + versioned predecessors + v1u integrity PASS')
PY
printf '[2/8] 49 new contextual C P bank/adversarial tests\n'
PYTHONPATH=. python3 -m pytest -q tests/test_spk_native_learning_v1_contextual.py
printf '[3/8] Native-v1/v1r/v1s/v1t inherited original PE/BV regressions\n'
PYTHONPATH=. python3 -m pytest -q tests/test_spk_native_learning_v1_generalized.py \
 tests/test_spk_native_learning_v1_serialized.py \
 tests/test_spk_native_learning_v1_durable.py \
 tests/test_spk_native_learning_v1.py
printf '[4/8] T14–T17 prior scientific/cryptographic regressions\n'
for dir in research/spk_v5_t17_macro_polarity/tests research/spk_v5_t16_macro_runtime/tests research/spk_v5_t15_macro_causal_learning/tests research/spk_v5_t14_macro_signed_source/tests; do
 PYTHONPATH=. python3 -m unittest discover -s "$dir" -q
done
printf '[5/8] Original-source contextual bank conformance A\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.contextual_conformance_v1u "$TMP/a.json" --root . --parent "$PARENT"
printf '[6/8] Original-source contextual bank conformance B, byte-equal oracle\n'
PYTHONPATH=. python3 -m spk_native_learning_v1.contextual_conformance_v1u "$TMP/b.json" --root . --parent "$PARENT"
cmp -- "$TMP/a.json" "$TMP/b.json"
printf '[7/8] Strict scoped acceptance + fresh frozen source pin check\n'
PYTHONPATH=. python3 - "$TMP/a.json" <<'PY'
import json,sys
from spk_native_learning_v1.generalized_case_v1t import pin_sources
x=json.load(open(sys.argv[1]))
assert x['status']=='NATIVE_V1U_CONTEXTUAL_P_SAME_SCHEDULER_CAUSAL_PASS'
assert x['original_frozen_pins']==pin_sources('.')
assert x['contextual_epoch_count']==5 and x['committed_tick_rows']==325
assert x['contextual_versions']==[2,1,2,1,3] and x['contextual_grants']==[2,1,0,0,1]
assert x['second_run_new_tick_rows']==0 and len(x['restart_cuts'])==7
assert x['context_order_independent_P_bank'] and x['prior_tamper']=='REJECTED'
assert x['native_v1_research_learning'] and not x['frozen_original_BV_learning']
assert x['host_controls_context_labels'] and not x['promotion_allowed']
print('  SAME-SCHEDULER C MULTI-CONTEXT P RECALL PASS; ORIGINAL V0E UNMODIFIED')
PY
printf '[8/8] Publish immutable report\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/a.json" "$OUT"
sha256sum -- "$OUT"
echo 'SPK NATIVE LEARNING V1U CONTEXTUAL P BANK CAUSAL REPLAY PASS; ORIGINAL BV UNMODIFIED'
