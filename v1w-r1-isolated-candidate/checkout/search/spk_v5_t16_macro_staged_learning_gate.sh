#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t16-macro-staged-learning.json}"
PARENT="$HOME/workspace/spk-evidence/spk-v5-t15-macro-prospective-learning.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T16 DENIED: REPORT_ALREADY_EXISTS' >&2; exit 3; }
[[ -f "$PARENT" && ! -L "$PARENT" ]] || { echo 'T16 DENIED: PARENT_T15_MISSING' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-t16-staged-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] Immutable ancestor SHA, original SPK sources, 27 manifest custody checks\n'
PYTHONPATH=. python3 - "$PARENT" <<'PY'
import sys,json,re,hashlib
from pathlib import Path
from research.spk_v5_t12_macro_native_memory_seam.native_bridge_v1d import sha,pinned_source_catalog
from research.spk_v5_t13_macro_original_access_guard.macro_gate import PE_SHA,BV_SHA
from research.spk_v5_t13_macro_original_access_guard.access_guard_v1 import ORIGINAL_A1D_SHA
from research.spk_v5_t16_macro_runtime.macro_gate import PARENT_SHA,PE_SHA as T16_PE
assert sha(sys.argv[1])==PARENT_SHA,'T16_PARENT_FWORK_SHA_MISMATCH'
assert sha('research/spk_v5_t16_macro_runtime/reference/t15-prospective-fwork.json')==PARENT_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA==T16_PE,'T16_FROZEN_PE_SOURCE_DRIFT'
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA,'T16_FROZEN_BV_SOURCE_DRIFT'
assert sha('spk_architecture_v1/pe_fault_v1d.py')==ORIGINAL_A1D_SHA,'T16_FROZEN_A1D_SOURCE_DRIFT'
assert pinned_source_catalog('.',require_sources=True)['original_count']==5
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
 't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
 't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza',
 't9abc_def_ghi','t9jkl_mno_pqr','t9stu_vwx_yza','t10abc_def_ghi',
 't10jkl_mno_pqr','t10stu_vwx_yza','t11_macro_memory_v1',
 't12_macro_native_memory_seam','t13_macro_original_access_guard',
 't14_macro_signed_source','t15_macro_causal_learning','t16_macro_runtime')
assert len(names)==27
legacy={'t4zabc','t5abc','t5def','t5ghi','t5jkl'}
for name in names:
 p=Path('research')/('spk_v5_'+name)/'manifest.json'
 assert p.is_file() and not p.is_symlink(),f'MANIFEST_MISSING:{name}'
 m=json.loads(p.read_text())
 assert (m.get('promotion_allowed',False) is False if name in legacy else
         m.get('promotion_allowed') is False),f'PROMOTION_UNSAFE:{name}'
 for field in ('native_learning','frozen_components_modified'):
  assert m.get(field,False) is False, f'FALSE_NATIVE_CLAIM:{name}:{field}'
 for rel,pin in m['files'].items():
  f=Path(rel)
  if f.suffix=='.pyc' or '__pycache__' in f.parts:
   assert name=='t7abc_def_ghi' and f.parent.name=='__pycache__','CACHE_NOT_LEGACY_T7'
   match=re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*)\.cpython-\d+(?:\.opt-[12])?\.pyc',f.name)
   assert match, f'CACHE_INVALID:{rel}'
   source=f.parent.parent/(match.group(1)+'.py')
   assert str(source) in m['files'],f'CACHE_SOURCE_NOT_PINNED:{rel}'
   continue
  assert f.is_file() and not f.is_symlink() and sha(f)==pin, f'SOURCE_MANIFEST_SHA_DRIFT:{rel}'
for name in ('docs/spk-v5-t12-v1c-hotfix-manifest.json','docs/spk-v5-t12-v1d-hotfix-manifest.json'):
 m=json.loads(Path(name).read_text())
 for rel,pin in m['files'].items():
  f=Path(rel);assert f.is_file() and not f.is_symlink() and sha(f)==pin, f'T12_HOTFIX_SHA_DRIFT:{rel}'
from research.spk_v5_t5mno import t5mno
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  27 cumulative manifests and all original SHA source pins PASS')
PY
printf '[2/8] Authentic frozen scheduler and original PE/A1d provenance preflight\n'
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
print('  original A1d, frozen PE, frozen BV-v0e verified; no native learning inferred')
PY
printf '[3/8] New T16 staged causal scientific & adversarial suite\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t16_macro_runtime/tests -q
printf '[4/8] First genuine frozen-PE staged experiment and independent T15 parity\n'
PYTHONPATH=. python3 -m research.spk_v5_t16_macro_runtime.macro_gate --root . --out "$TMP/first.json"
printf '[5/8] Full inherited regressions from T15 back to T4ZABC\n'
for name in t15_macro_causal_learning t14_macro_signed_source t13_macro_original_access_guard t12_macro_native_memory_seam t11_macro_memory_v1 t10stu_vwx_yza t10jkl_mno_pqr t10abc_def_ghi t9stu_vwx_yza t9jkl_mno_pqr t9abc_def_ghi t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[6/8] Second independent full report, exact byte equality\n'
PYTHONPATH=. python3 -m research.spk_v5_t16_macro_runtime.macro_gate --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
printf '[7/8] Scientific acceptance, provenance, boundaries, no false nativism\n'
PYTHONPATH=. python3 - "$TMP/first.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['schema']=='spk-v5-t16-owned-staged-causal-learning/research-v0'
assert r['stages']==['C_PE','WORLD','A_PE','B_RELAY','C_CREDIT']
assert r['transaction_scope']=='ONE_DURABLE_TRANSACTION_PER_STAGE'
assert r['independent_T15_parity']['paired_case_count']==60
assert r['independent_T15_parity']['all_five_modes'] and r['independent_T15_parity']['reversed_actuator']
assert r['heldout_P_frozen'] and r['staged_dispatch_slots']>0
assert all(r['totals'][x]['training_P_commits']==0 for x in ('frozen','no_feedback','altered','wrong_lineage'))
assert r['original_SPK_native_P_grants']==0 and r['native_SPK_learning'] is False
assert r['native_frozen_BV_semantic_credit'] is False and r['promotion_allowed'] is False
assert r['T13_A1d_original_memory_permission_per_thermal_credit'] is False
assert r['T14_signed_sensor_attestation'] is False
assert r['status'] in ('STAGED_CAUSAL_LEARNING_LIMITED_SUPPORTED','STAGED_CAUSAL_LEARNING_NOT_SUPPORTED')
print('  Scientific status:',r['status'],'gain',r['totals']['frozen']['heldout_improved'],
      '->',r['totals']['adaptive']['heldout_improved'])
print('  60 individual paired-case choice parities, no native learning claimed')
PY
printf '[8/8] Repeat original SHA and publish the unchanged deterministic report\n'
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
echo 'T16 MACRO STAGED A-COMPUTED CAUSAL LEARNING PARITY PASS; LIMITED RESEARCH RUNTIME; ZERO ORIGINAL SPK NATIVE LEARNING'
