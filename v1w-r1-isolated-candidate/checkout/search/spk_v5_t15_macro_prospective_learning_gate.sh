#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t15-macro-prospective-learning.json}"
PARENT="$HOME/workspace/spk-evidence/spk-v5-t14-macro-signed-source.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T15 DENIED: REPORT_EXISTS' >&2; exit 3; }
[[ -f "$PARENT" && ! -L "$PARENT" ]] || { echo 'T15 DENIED: T14_REPORT_MISSING' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-t15-prospective-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] Original SHA, 26 immutable cumulative manifests, T14 authentic parent\n'
PYTHONPATH=. python3 - "$PARENT" <<'PY'
import sys,json,re
from pathlib import Path
from research.spk_v5_t12_macro_native_memory_seam.native_bridge_v1d import sha,pinned_source_catalog
from research.spk_v5_t13_macro_original_access_guard.macro_gate import PE_SHA,BV_SHA
from research.spk_v5_t13_macro_original_access_guard.access_guard_v1 import ORIGINAL_A1D_SHA
from research.spk_v5_t15_macro_causal_learning.prospective_gate import PARENT_T14_SHA,PE_SHA as T15_PE
assert sha(sys.argv[1])==PARENT_T14_SHA, 'T14_PARENT_FWORK_REPORT_DRIFT'
assert sha('research/spk_v5_t15_macro_causal_learning/reference/t14-lab-signed-source.json')==PARENT_T14_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA==T15_PE, 'PE_SOURCE_DRIFT'
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA, 'BV_SOURCE_DRIFT'
assert sha('spk_architecture_v1/pe_fault_v1d.py')==ORIGINAL_A1D_SHA, 'A1D_SOURCE_DRIFT'
assert pinned_source_catalog('.',require_sources=True)['original_count']==5
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
 't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
 't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza',
 't9abc_def_ghi','t9jkl_mno_pqr','t9stu_vwx_yza','t10abc_def_ghi',
 't10jkl_mno_pqr','t10stu_vwx_yza','t11_macro_memory_v1',
 't12_macro_native_memory_seam','t13_macro_original_access_guard',
 't14_macro_signed_source','t15_macro_causal_learning')
legacy={'t4zabc','t5abc','t5def','t5ghi','t5jkl'}
for name in names:
 path=Path('research')/('spk_v5_'+name)/'manifest.json'
 assert path.is_file() and not path.is_symlink(), f'MANIFEST_MISSING:{name}'
 m=json.loads(path.read_text())
 assert (m.get('promotion_allowed',False) is False if name in legacy else
         m.get('promotion_allowed') is False),f'MANIFEST_PROMOTION:{name}'
 for field in ('native_learning','frozen_components_modified'):
  assert m.get(field,False) is False, f'FALSE_CLAIM:{name}:{field}'
 for rel,pin in m['files'].items():
  f=Path(rel)
  if f.suffix=='.pyc' or '__pycache__' in f.parts:
   assert name=='t7abc_def_ghi' and f.parent.name=='__pycache__','CACHE_OUTSIDE_HISTORICAL_T7'
   match=re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*)\.cpython-\d+(?:\.opt-[12])?\.pyc',f.name)
   assert match, f'CACHE_UNRECOGNIZED:{rel}'
   source=f.parent.parent/(match.group(1)+'.py')
   assert str(source) in m['files'],f'CACHE_SOURCE_NOT_PINNED:{rel}'
   continue
  assert f.is_file() and not f.is_symlink() and sha(f)==pin, f'MANIFEST_SHA_DRIFT:{rel}'
from research.spk_v5_t5mno import t5mno
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
for name in ('docs/spk-v5-t12-v1c-hotfix-manifest.json','docs/spk-v5-t12-v1d-hotfix-manifest.json'):
 manifest=json.loads(Path(name).read_text())
 for rel,pin in manifest['files'].items():
  f=Path(rel)
  assert f.is_file() and not f.is_symlink() and sha(f)==pin, f'HOTFIX_SHA_DRIFT:{rel}'
print('  26 manifests, 12 frozen source pins, PE/BV/A1d, five memory APIs and T14 report PASS')
PY
printf '[2/8] Real original BV and PE preflight (no test stubs permitted)\n'
PYTHONPATH=. python3 - <<'PY'
import inspect
from spk_architecture_v1.pe_fault_v1d import execute_failstop_v1d
from spk_architecture_v1.pe_execution_v1b import _compute_local
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
assert inspect.getmodule(execute_failstop_v1d).__name__=='spk_architecture_v1.pe_fault_v1d'
assert inspect.getmodule(_compute_local).__name__=='spk_architecture_v1.pe_execution_v1b'
for c,g in ((11,11),(11,12),(12,11),(12,12)):
 _,report=execute_raw(c,g)
 assert report['full_BV_scheduler'] and report['reverse_A_B_C']
print('  frozen original computational modules and original BV preflight PASS')
PY
printf '[3/8] New prospective source/PE/credit scientific tests\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t15_macro_causal_learning/tests -q
printf '[4/8] Independent prospective falsification report, first run\n'
PYTHONPATH=. python3 -m research.spk_v5_t15_macro_causal_learning.prospective_gate --root . --out "$TMP/first.json"
printf '[5/8] Inherited 25 checkpoint regressions, full\n'
for name in t14_macro_signed_source t13_macro_original_access_guard t12_macro_native_memory_seam t11_macro_memory_v1 t10stu_vwx_yza t10jkl_mno_pqr t10abc_def_ghi t9stu_vwx_yza t9jkl_mno_pqr t9abc_def_ghi t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[6/8] Second full prospective experiment; byte-identical report\n'
PYTHONPATH=. python3 -m research.spk_v5_t15_macro_causal_learning.prospective_gate --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
printf '[7/8] Blind split, causal controls, honest no-promotion boundary\n'
PYTHONPATH=. python3 - "$TMP/first.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['schema']=='spk-v5-t15-prospective-A-computed-feedback-falsification/research-v0'
assert r['experiment_precommit']['positive_margin_absolute']==0.10
assert r['experiment_precommit']['training_temperatures_even']==[0,2,4,6,8,10,12,14]
assert r['experiment_precommit']['heldout_temperatures_odd']==[1,3,5,7,9,11,13,15]
assert r['evaluation_has_no_P_writes'] and r['negative_controls_fail_closed']
assert all(v['heldout_cases']==225 for v in r['totals'].values())
assert r['totals']['adaptive']['training_P_commits']>0
assert r['reversed_actuator_counterfactual']['adaptive']['cases']==75
assert r['original_frozen_sPK_P_learning'] is False and r['promotion_allowed'] is False
assert r['status'] in ('RESTRICTED_CAUSAL_LEARNING_SUPPORTED',
                       'RESTRICTED_CAUSAL_LEARNING_NOT_SUPPORTED')
print('  Scientific hypothesis result:',r['status'])
print('  heldout physically improved:',r['totals']['frozen']['heldout_improved'],
      '->',r['totals']['adaptive']['heldout_improved'],'out of 225')
print('  reverse-physics score:',r['reversed_actuator_counterfactual']['adaptive']['hits'],
      'out of 75; zero frozen SPK native learning')
PY
printf '[8/8] Verify original sources remain frozen and publish once\n'
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
echo 'T15 MACRO PROSPECTIVE A-COMPUTED FEEDBACK FALSIFICATION COMPLETE; LIMITED CAUSAL RESULT, ZERO ORIGINAL SPK NATIVE LEARNING'
