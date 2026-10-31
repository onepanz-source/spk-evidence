#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t12-macro-native-memory-seam.json}"
PREV="$HOME/workspace/spk-evidence/spk-v5-t11-macro-owned-memory-v1.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T12 FAIL CLOSED: REPORT_ALREADY_EXISTS' >&2; exit 3; }
[[ -f "$PREV" && ! -L "$PREV" ]] || { echo 'T12 FAIL CLOSED: MISSING_T11_FWORK_REPORT' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-t12-original-memory-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] Parent original evidence and 23 manifests (historical-source-aware v1c)\n'
PYTHONPATH=. python3 - "$PREV" <<'PY'
import sys,json
from pathlib import Path
from research.spk_v5_t12_macro_native_memory_seam.native_bridge import sha,PINNED,pinned_source_catalog
from research.spk_v5_t12_macro_native_memory_seam.macro_gate import T11_FWORK_SHA,PE_SHA,BV_SHA
assert sha(sys.argv[1])==T11_FWORK_SHA, 'PARENT_T11_FWORK_SHA_DRIFT'
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
 't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
 't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza',
 't9abc_def_ghi','t9jkl_mno_pqr','t9stu_vwx_yza','t10abc_def_ghi',
 't10jkl_mno_pqr','t10stu_vwx_yza','t11_macro_memory_v1','t12_macro_native_memory_seam')
# These five older research manifests predate the explicit promotion field.
# File integrity remains mandatory for ALL manifests, without exceptions.
legacy_no_promotion_field={'t4zabc','t5abc','t5def','t5ghi','t5jkl'}
for name in names:
 p=Path('research')/('spk_v5_'+name)/'manifest.json'
 assert p.is_file() and not p.is_symlink(),f'MISSING_MANIFEST:{name}'
 m=json.loads(p.read_text())
 if name in legacy_no_promotion_field:
  assert m.get('promotion_allowed',False) is False,f'LEGACY_PROMOTION_DRIFT:{name}'
 else:
  assert m.get('promotion_allowed') is False,f'PROMOTION_MISSING_OR_DRIFT:{name}'
 for flag in ('frozen_components_modified','native_learning'):
  assert m.get(flag,False) is False,f'PROHIBITED_HISTORICAL_FLAG:{name}:{flag}'
 # Historical T7ABC cache entries are implementation artifacts.
 # The exact list can vary by historical checkout or archive packaging.
 # Never trust .pyc bytes as a source authority; require and hash each
 # corresponding pinned .py source, and reject caches in any other milestone.
 import re
 cache_count=0
 for rel,pinned in m['files'].items():
  f=Path(rel)
  if rel.endswith('.pyc') or '__pycache__' in f.parts:
   assert name=='t7abc_def_ghi',f'UNEXPECTED_HISTORICAL_CACHE:{name}:{rel}'
   assert f.parent.name=='__pycache__',f'MALFORMED_CACHE_PATH:{rel}'
   assert rel.startswith('research/spk_v5_t7abc_def_ghi/'),f'CACHE_OUTSIDE_T7ABC:{rel}'
   match=re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*)\.cpython-\d+(?:\.opt-[12])?\.pyc',f.name)
   assert match,f'UNRECOGNIZED_CACHE_NAME:{rel}'
   py=f.parent.parent/(match.group(1)+'.py')
   assert str(py) in m['files'],f'UNCOVERED_BYTECODE_SOURCE:{rel}'
   assert isinstance(m['files'][str(py)],str) and len(m['files'][str(py)])==64,f'UNPINNED_SOURCE_HASH:{rel}'
   cache_count+=1
   continue
  assert f.is_file() and not f.is_symlink() and sha(f)==pinned,f'MANIFEST_DRIFT:{rel}'
 # T7ABC's .pyc list MAY be empty, partial or complete: no fixed-set assertion.
 # The .py sources above are necessarily also checked by the regular SHA loop.
 if name=='t7abc_def_ghi':
  print(f'  T7ABC historical cache artifacts excluded: {cache_count}; source SHA pins enforced')
original=pinned_source_catalog('.',require_sources=True)
assert original['original_count']==5
from research.spk_v5_t5mno import t5mno
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  original source hashes, native memory API pins, 23 manifests PASS (v1b)')
PY
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
import json,hashlib
m=json.loads(Path('docs/spk-v5-t12-v1c-hotfix-manifest.json').read_text())
for rel,s in m['files'].items():
 p=Path(rel)
 assert p.is_file() and not p.is_symlink(), 'MISSING_V1C_HOTFIX:'+rel
 assert hashlib.sha256(p.read_bytes()).hexdigest()==s, 'T12_V1C_HOTFIX_DRIFT:'+rel
print('  T12 v1c source pin PASS')
PY
printf '[2/8] Genuine original BV-v0e source preflight\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
for c in (11,12):
 for g in (11,12):
  _,x=execute_raw(c,g)
  assert x['full_BV_scheduler'] and x['reverse_A_B_C']
_,x=execute_raw(12,11,drop_forward=True)
assert not x['reverse_A_B_C']
print('  original scheduler admission PASS')
PY
printf '[3/8] Actual original frozen memory admission + projection + access authority, first run\n'
PYTHONPATH=. python3 -m research.spk_v5_t12_macro_native_memory_seam.macro_gate_v1c --root . --out "$TMP/one.json"
printf '[4/8] All 23 cumulative regressions (no historical skip)\n'
for name in t12_macro_native_memory_seam t11_macro_memory_v1 t10stu_vwx_yza t10jkl_mno_pqr t10abc_def_ghi t9stu_vwx_yza t9jkl_mno_pqr t9abc_def_ghi t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[5/8] Independent repeated original invocation, identical deterministic evidence\n'
PYTHONPATH=. python3 -m research.spk_v5_t12_macro_native_memory_seam.macro_gate_v1c --root . --out "$TMP/two.json"
cmp -- "$TMP/one.json" "$TMP/two.json"
printf '[6/8] Explicit source-access / learning-P custody separation\n'
python3 - "$TMP/one.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));n=r['M2_original_memory_execution_probe']['counts']
assert r['M1_original_source_pin_catalog']['original_count']==5
assert r['M2_original_memory_execution_probe']['original_api_attempts']==4
assert n['native_execution_memory_admissions']>=1
assert r['M4_versioned_new_runtime_P_parity']['new_v1_memory_grants']==8
assert (r['M4_versioned_new_runtime_P_parity']['naive_three']['successes'],r['M4_versioned_new_runtime_P_parity']['context_affinity']['successes'])==(84,88)
a=r['M6_promotion_and_native_learning_boundary']
assert a['frozen_original_P_learning_grants']==a['frozen_original_P_learning_writes']==0
assert a['frozen_original_BV_semantic_deliveries']==0 and not a['frozen_original_learning'] and not a['promote_to_frozen_original']
assert not r['promotion_allowed'] and not r['native_learning']
print('  original execution memory admission >=1; learning-P original 0; exactly separated')
PY
printf '[7/8] Original files unchanged after dynamic invocation\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t12_macro_native_memory_seam.native_bridge import pinned_source_catalog
from research.spk_v5_t12_macro_native_memory_seam.macro_gate import PE_SHA,BV_SHA,sha
assert pinned_source_catalog('.',require_sources=True)['original_count']==5
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
print('  original source unchanged PASS')
PY
printf '[8/8] Immutable cumulative report publication\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/one.json" "$OUT"
sha256sum -- "$OUT"
echo 'T12 V1C MACRO ORIGINAL MEMORY EXECUTION API ADMISSION PASS; ORIGINAL EXECUTION ACCESS SEPARATE FROM P LEARNING; ZERO ORIGINAL BV LEARNING'
