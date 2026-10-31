#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t17-macro-unknown-actuator.json}"
PARENT="$HOME/workspace/spk-evidence/spk-v5-t16-macro-staged-learning.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T17 DENIED: REPORT_ALREADY_EXISTS' >&2; exit 3; }
[[ -f "$PARENT" && ! -L "$PARENT" ]] || { echo 'T17 DENIED: T16_PARENT_MISSING' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-t17-unknown-actuator-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] Signed history: T16 fwork parent and 28 source-bound manifests\n'
PYTHONPATH=. python3 - "$PARENT" <<'PY'
import sys,json,re,hashlib
from pathlib import Path
from research.spk_v5_t12_macro_native_memory_seam.native_bridge_v1d import sha,pinned_source_catalog
from research.spk_v5_t13_macro_original_access_guard.macro_gate import PE_SHA,BV_SHA
from research.spk_v5_t13_macro_original_access_guard.access_guard_v1 import ORIGINAL_A1D_SHA
from research.spk_v5_t17_macro_polarity.macro_gate import PARENT_SHA,PE_SHA as T17_PE
assert sha(sys.argv[1])==PARENT_SHA,'T17_T16_PARENT_FWORK_MISMATCH'
assert sha('research/spk_v5_t17_macro_polarity/reference/t16-fwork.json')==PARENT_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA==T17_PE,'T17_FROZEN_PE_SOURCE_DRIFT'
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'T17_FROZEN_BV_SOURCE_DRIFT'
assert sha('spk_architecture_v1/pe_fault_v1d.py')==ORIGINAL_A1D_SHA,'T17_FROZEN_A1D_SOURCE_DRIFT'
assert pinned_source_catalog('.',require_sources=True)['original_count']==5
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
 't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
 't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza',
 't9abc_def_ghi','t9jkl_mno_pqr','t9stu_vwx_yza','t10abc_def_ghi',
 't10jkl_mno_pqr','t10stu_vwx_yza','t11_macro_memory_v1',
 't12_macro_native_memory_seam','t13_macro_original_access_guard',
 't14_macro_signed_source','t15_macro_causal_learning','t16_macro_runtime',
 't17_macro_polarity')
assert len(names)==28
legacy={'t4zabc','t5abc','t5def','t5ghi','t5jkl'}
for name in names:
 p=Path('research')/('spk_v5_'+name)/'manifest.json'
 assert p.is_file() and not p.is_symlink(),f'MANIFEST_MISSING:{name}'
 m=json.loads(p.read_text())
 assert (m.get('promotion_allowed',False) is False if name in legacy else
         m.get('promotion_allowed') is False),f'PROMOTION_UNSAFE:{name}'
 for field in ('native_learning','frozen_components_modified'):
  assert m.get(field,False) is False,f'FALSE_NATIVE_CLAIM:{name}:{field}'
 for rel,pin in m['files'].items():
  f=Path(rel)
  if f.suffix=='.pyc' or '__pycache__' in f.parts:
   assert name=='t7abc_def_ghi' and f.parent.name=='__pycache__','CACHE_NOT_LEGACY_T7'
   match=re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*)\.cpython-\d+(?:\.opt-[12])?\.pyc',f.name)
   assert match,f'CACHE_INVALID:{rel}'
   source=f.parent.parent/(match.group(1)+'.py')
   assert str(source) in m['files'],f'CACHE_SOURCE_NOT_PINNED:{rel}'
   continue
  assert f.is_file() and not f.is_symlink() and sha(f)==pin,f'SOURCE_MANIFEST_SHA_DRIFT:{rel}'
for doc in ('docs/spk-v5-t12-v1c-hotfix-manifest.json','docs/spk-v5-t12-v1d-hotfix-manifest.json'):
 m=json.loads(Path(doc).read_text())
 for rel,pin in m['files'].items():
  f=Path(rel);assert f.is_file() and not f.is_symlink() and sha(f)==pin,f'T12_HOTFIX_DRIFT:{rel}'
from research.spk_v5_t5mno import t5mno
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  Original five memory API pins, 28 manifests and all SHA pins PASS')
PY
printf '[2/8] Frozen original PE/BV/A1d provenance (not claims of native learning)\n'
PYTHONPATH=. python3 - <<'PY'
import inspect
from spk_architecture_v1.pe_execution_v1b import _compute_local
from spk_architecture_v1.pe_fault_v1d import execute_failstop_v1d
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
assert inspect.getmodule(_compute_local).__name__=='spk_architecture_v1.pe_execution_v1b'
assert inspect.getmodule(execute_failstop_v1d).__name__=='spk_architecture_v1.pe_fault_v1d'
for c,g in ((11,11),(11,12),(12,11),(12,12)):
 _,r=execute_raw(c,g)
 assert r['full_BV_scheduler'] and r['reverse_A_B_C']
print('  Frozen source provenance PASS; no original-BV learning asserted')
PY
printf '[3/8] New T17 PE response-sign and adversarial 42-test suite\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t17_macro_polarity/tests -q
printf '[4/8] First actual frozen-PE feedback science experiment (both actuator polarities)\n'
PYTHONPATH=. python3 -m research.spk_v5_t17_macro_polarity.macro_gate --root . --out "$TMP/first.json"
printf '[5/8] All inherited T16->T4ZABC regression suites\n'
for name in t16_macro_runtime t15_macro_causal_learning t14_macro_signed_source t13_macro_original_access_guard t12_macro_native_memory_seam t11_macro_memory_v1 t10stu_vwx_yza t10jkl_mno_pqr t10abc_def_ghi t9stu_vwx_yza t9jkl_mno_pqr t9abc_def_ghi t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[6/8] Independent second scientific experiment and byte-for-byte comparison\n'
PYTHONPATH=. python3 -m research.spk_v5_t17_macro_polarity.macro_gate --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
printf '[7/8] Precommitted hypothesis and native-learning boundaries\n'
PYTHONPATH=. python3 - "$TMP/first.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['schema']=='spk-v5-t17-dual-P-unknown-actuator-causal-learning/research-v0'
assert r['parent_T16_sha256']=='e768acd122f39c38dfb3c3dee8df2c1d3e74479beb53be1a5e746a957dd6d2ca'
assert r['all_heldout_P_frozen'] and r['audited_cell_count']==360
assert r['independent_T16_baseline_reproduced']
assert r['scientific_precommit']['initial_sign']==0
for plant in ('normal','reversed'):
 a=r['totals'][plant]['adaptive'];f=r['totals'][plant]['frozen']
 assert a['cases']==f['cases']==225
 assert all(r['totals'][plant][mode]['P_grants']==0 for mode in
            ('frozen','no_feedback','altered','wrong_lineage','effect_tamper'))
 assert a['correct_sign']==30 or r['status'].endswith('NOT_SUPPORTED')
assert r['status'] in ('BOUNDED_UNKNOWN_ACTUATOR_LEARNING_SUPPORTED',
                      'BOUNDED_UNKNOWN_ACTUATOR_LEARNING_NOT_SUPPORTED')
assert not r['original_T13_A1d_thermal_P_access'] and not r['original_T14_signed_thermal_source']
assert r['original_SPK_BV_native_P_grants']==0 and not r['original_SPK_native_learning']
assert r['promotion_allowed'] is False
print('  SCIENTIFIC STATUS:',r['status'])
print('  forward:',r['totals']['normal']['frozen']['hits'],'->',r['totals']['normal']['adaptive']['hits'])
print('  reversed:',r['totals']['reversed']['frozen']['hits'],'->',r['totals']['reversed']['adaptive']['hits'])
PY
printf '[8/8] Final SHA guard and publish immutable report\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t12_macro_native_memory_seam.native_bridge_v1d import sha,pinned_source_catalog
from research.spk_v5_t13_macro_original_access_guard.macro_gate import PE_SHA,BV_SHA
from research.spk_v5_t13_macro_original_access_guard.access_guard_v1 import ORIGINAL_A1D_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert sha('spk_architecture_v1/pe_fault_v1d.py')==ORIGINAL_A1D_SHA
assert pinned_source_catalog('.',require_sources=True)['original_count']==5
PY
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
STATUS="$(PYTHONPATH=. python3 - "$OUT" <<'PY_STATUS'
import json,sys
print(json.load(open(sys.argv[1]))['status'])
PY_STATUS
)"
if [[ "$STATUS" == 'BOUNDED_UNKNOWN_ACTUATOR_LEARNING_SUPPORTED' ]]; then
 echo 'T17 MACRO BOUNDED UNKNOWN ACTUATOR PE-OBSERVED LEARNING SUPPORTED; ZERO ORIGINAL SPK NATIVE P LEARNING'
else
 echo 'T17 MACRO SCIENTIFIC HYPOTHESIS NOT SUPPORTED; SOFTWARE GATE PASS; ZERO ORIGINAL SPK NATIVE P LEARNING'
fi
