#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t13-macro-original-access-guard.json}"
PARENT="$HOME/workspace/spk-evidence/spk-v5-t12-macro-native-memory-seam.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T13 FAIL CLOSED: REPORT_ALREADY_EXISTS' >&2; exit 3; }
[[ -f "$PARENT" && ! -L "$PARENT" ]] || { echo 'T13 FAIL CLOSED: T12_FWORK_REPORT_MISSING' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-t13-original-access-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] T12 authentic evidence and 24 cumulative manifests\n'
PYTHONPATH=. python3 - "$PARENT" <<'PY'
import sys,json,re
from pathlib import Path
from research.spk_v5_t12_macro_native_memory_seam.native_bridge_v1d import sha,pinned_source_catalog
from research.spk_v5_t13_macro_original_access_guard.macro_gate import PARENT_T12_SHA,PE_SHA,BV_SHA
from research.spk_v5_t13_macro_original_access_guard.access_guard_v1 import ORIGINAL_A1D_SHA
assert sha(sys.argv[1])==PARENT_T12_SHA, 'T12_FWORK_SHA_DRIFT'
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA, 'ORIGINAL_PE_DRIFT'
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA, 'ORIGINAL_BV_DRIFT'
assert sha('spk_architecture_v1/pe_fault_v1d.py')==ORIGINAL_A1D_SHA, 'ORIGINAL_A1D_DRIFT'
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
 't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
 't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza',
 't9abc_def_ghi','t9jkl_mno_pqr','t9stu_vwx_yza','t10abc_def_ghi',
 't10jkl_mno_pqr','t10stu_vwx_yza','t11_macro_memory_v1',
 't12_macro_native_memory_seam','t13_macro_original_access_guard')
legacy={'t4zabc','t5abc','t5def','t5ghi','t5jkl'}
for name in names:
 path=Path('research')/('spk_v5_'+name)/'manifest.json'
 assert path.is_file() and not path.is_symlink(), f'MANIFEST_MISSING:{name}'
 m=json.loads(path.read_text())
 assert m.get('promotion_allowed',False) is False if name in legacy else m.get('promotion_allowed') is False, f'PROMOTION_SCHEMA:{name}'
 for flag in ('frozen_components_modified','native_learning'):
  assert m.get(flag,False) is False, f'NATIVE_CLAIM:{name}:{flag}'
 for rel,pin in m['files'].items():
  path=Path(rel)
  if rel.endswith('.pyc') or '__pycache__' in path.parts:
   assert name=='t7abc_def_ghi' and path.parent.name=='__pycache__',f'CACHE_OUTSIDE_T7ABC:{rel}'
   assert rel.startswith('research/spk_v5_t7abc_def_ghi/'),f'CACHE_OUTSIDE_T7ABC:{rel}'
   match=re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*)\.cpython-\d+(?:\.opt-[12])?\.pyc',path.name)
   assert match, f'CACHE_INVALID:{rel}'
   source=path.parent.parent/(match.group(1)+'.py')
   assert str(source) in m['files'] and len(m['files'][str(source)])==64,f'CACHE_SOURCE_NOT_PINNED:{rel}'
   continue
  assert path.is_file() and not path.is_symlink() and sha(path)==pin, f'MANIFEST_DRIFT:{rel}'
assert pinned_source_catalog('.',require_sources=True)['original_count']==5
from research.spk_v5_t5mno import t5mno
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
# Also verify versioned T12 v1c and v1d additive hotfixes, whose manifests
# are deliberately distinct from historical T12 macro manifest.
for name in ('docs/spk-v5-t12-v1c-hotfix-manifest.json','docs/spk-v5-t12-v1d-hotfix-manifest.json'):
 data=json.loads(Path(name).read_text())
 for rel,pin in data['files'].items():
  p=Path(rel)
  assert p.is_file() and not p.is_symlink() and sha(p)==pin, f'T12_HOTFIX_SOURCE_DRIFT:{rel}'
print('  original PE/BV/A1d, five original Memory APIs, 12 original source pins, 24 manifests PASS')
PY
printf '[2/8] Original BV source admission and original A1d producer availability\n'
PYTHONPATH=. python3 - <<'PY'
import inspect
from spk_architecture_v1.pe_fault_v1d import execute_failstop_v1d
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
assert inspect.getmodule(execute_failstop_v1d).__name__=='spk_architecture_v1.pe_fault_v1d'
for c,g in ((11,11),(11,12),(12,11),(12,12)):
 _,r=execute_raw(c,g)
 assert r['full_BV_scheduler'] and r['reverse_A_B_C']
print('  authentic original BV-v0e and A1d producer PASS')
PY
printf '[3/8] T13 direct unit tests (no test witness can promote to original)\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t13_macro_original_access_guard/tests -q
printf '[4/8] ORIGINAL memory APIs invoked INSIDE reference C tick, strict source mode\n'
PYTHONPATH=. python3 -m research.spk_v5_t13_macro_original_access_guard.macro_gate --root . --out "$TMP/one.json"
printf '[5/8] Full inherited regression suites (23 checkpoints)\n'
for name in t12_macro_native_memory_seam t11_macro_memory_v1 t10stu_vwx_yza t10jkl_mno_pqr t10abc_def_ghi t9stu_vwx_yza t9jkl_mno_pqr t9abc_def_ghi t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[6/8] Second independent complete authentic tick run; byte equality\n'
PYTHONPATH=. python3 -m research.spk_v5_t13_macro_original_access_guard.macro_gate --root . --out "$TMP/two.json"
cmp -- "$TMP/one.json" "$TMP/two.json"
printf '[7/8] Exact original-access custody, legacy learning prohibition\n'
python3 - "$TMP/one.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));a=r['M3_reference_v1_runtime'];w=a['original_witness']
assert r['production_original_A1d_invoked_during_C_tick'] and not a['test_only']
assert a['episodes']==96 and (a['successes'],a['waves'],a['reference_P_grants'])==(88,48,8)
assert w['witness_kind']=='ORIGINAL_A1D_EXECUTION_ACCESS'
assert w['original_access_witnesses']==8 and w['test_only_witnesses']==0
assert w['original_A1d_executions_for_witnesses']==32
assert w['new_runtime_v1_P_grants']==8
assert a['v1_owned_memory_P_commits']==8 and a['original_SPK_learning_P_grants']==0
assert r['M4_old_vs_new']['old_rows_digest']==r['M4_old_vs_new']['new_rows_digest']
assert r['M5_boundary']['original_P_learning_grants']==r['M5_boundary']['original_BV_semantic_feedback']==0
assert not r['original_learning'] and not r['promotion_allowed'] and not r['native_learning']
print('  8 ORIGINAL execution-access witness prerequisites with 8 research P commits, native learning zero')
PY
printf '[8/8] Post-execution frozen source custody + immutable report\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t12_macro_native_memory_seam.native_bridge_v1d import sha,pinned_source_catalog
from research.spk_v5_t13_macro_original_access_guard.macro_gate import PE_SHA,BV_SHA
from research.spk_v5_t13_macro_original_access_guard.access_guard_v1 import ORIGINAL_A1D_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert sha('spk_architecture_v1/pe_fault_v1d.py')==ORIGINAL_A1D_SHA
assert pinned_source_catalog('.',require_sources=True)['original_count']==5
print('  original sources untouched PASS')
PY
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/one.json" "$OUT"
sha256sum -- "$OUT"
echo 'T13 MACRO ORIGINAL EXECUTION MEMORY ACCESS GATES LIVE REFERENCE C TICKS PASS; NO ORIGINAL BV P LEARNING'
