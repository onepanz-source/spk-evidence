#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t14-macro-signed-source.json}"
PARENT="$HOME/workspace/spk-evidence/spk-v5-t13-macro-original-access-guard.json"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T14 FAIL CLOSED: REPORT_ALREADY_EXISTS' >&2; exit 3; }
[[ -f "$PARENT" && ! -L "$PARENT" ]] || { echo 'T14 FAIL CLOSED: T13_FWORK_REPORT_MISSING' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-t14-signed-source-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] T13 authentic evidence and 25 cumulative manifests\n'
PYTHONPATH=. python3 - "$PARENT" <<'PY'
import sys,json,re
from pathlib import Path
from research.spk_v5_t12_macro_native_memory_seam.native_bridge_v1d import sha,pinned_source_catalog
from research.spk_v5_t13_macro_original_access_guard.macro_gate import PE_SHA,BV_SHA
from research.spk_v5_t14_macro_signed_source.macro_gate import PARENT_SHA
from research.spk_v5_t13_macro_original_access_guard.access_guard_v1 import ORIGINAL_A1D_SHA
assert sha(sys.argv[1])==PARENT_SHA, 'T13_FWORK_SHA_DRIFT'
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA, 'ORIGINAL_PE_DRIFT'
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA, 'ORIGINAL_BV_DRIFT'
assert sha('spk_architecture_v1/pe_fault_v1d.py')==ORIGINAL_A1D_SHA, 'ORIGINAL_A1D_DRIFT'
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
 't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
 't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza',
 't9abc_def_ghi','t9jkl_mno_pqr','t9stu_vwx_yza','t10abc_def_ghi',
 't10jkl_mno_pqr','t10stu_vwx_yza','t11_macro_memory_v1',
 't12_macro_native_memory_seam','t13_macro_original_access_guard',
 't14_macro_signed_source')
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
print('  original PE/BV/A1d, five original Memory APIs, 12 original source pins, 25 manifests PASS')
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
printf '[3/8] New signed-A-source adversarial suite\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t14_macro_signed_source/tests -q
printf '[4/8] STRICT T14 lab-signed receipts, genuine ORIGINAL A1d before each research P commit\n'
PYTHONPATH=. python3 -m research.spk_v5_t14_macro_signed_source.macro_gate --root . --out "$TMP/first.json"
printf '[5/8] Cumulative inherited regression suites (24 checkpoints)\n'
for name in t13_macro_original_access_guard t12_macro_native_memory_seam t11_macro_memory_v1 t10stu_vwx_yza t10jkl_mno_pqr t10abc_def_ghi t9stu_vwx_yza t9jkl_mno_pqr t9abc_def_ghi t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[6/8] Independent strict report; deterministic equality\n'
PYTHONPATH=. python3 -m research.spk_v5_t14_macro_signed_source.macro_gate --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
printf '[7/8] Source-key denial, matching original access and native-learning prohibition\n'
python3 - "$TMP/first.json" <<'PYREPORT'
import json,sys
r=json.load(open(sys.argv[1]))
a=r['M3_lab_signature_preserves_T13'];b=r['M2_unsigned_denial_and_recovery'];c=r['M4_recovery_parity'];m=r['M6_trust_and_promotion']
assert r['strict_original_execution'] and r['M5_original_A1d_memory_access_during_signed_C_grant']
assert (a['episodes'],a['successes'],a['waves'],a['grants'],a['attestation_grants'])==(96,88,48,8,8)
assert a['original_execution_access_witnesses']==8 and a['original_A1d_executions_for_witnesses']==32
assert a['test_only_memory_witnesses']==0 and a['generated_laboratory_signer']
assert c['row_digest']==a['row_digest'] and c['grants']==8 and c['original_execution_access_witnesses']==8
assert b['unsigned_negative_receipt_denied_atomically'] and b['P_grants_before_signature']==0 and b['P_grants_after_valid_signature']==1
assert m['real_external_signer_in_release'] is False and m['separate_independent_A_sensor_attested'] is False
assert m['original_SPK_P_learning_grants']==0 and m['native_BV_semantic_learning'] is False
assert r['native_learning'] is False and r['promotion_allowed'] is False
print('  signed LAB protocol+authentic A1d: eight reference P; unsigned fail-closed; ZERO native/source-authenticated learning')
PYREPORT
printf '[8/8] Original source pins after execution; publish report\n'
PYTHONPATH=. python3 - <<'PYFINAL'
from research.spk_v5_t12_macro_native_memory_seam.native_bridge_v1d import sha,pinned_source_catalog
from research.spk_v5_t13_macro_original_access_guard.macro_gate import PE_SHA,BV_SHA
from research.spk_v5_t13_macro_original_access_guard.access_guard_v1 import ORIGINAL_A1D_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert sha('spk_architecture_v1/pe_fault_v1d.py')==ORIGINAL_A1D_SHA
assert pinned_source_catalog('.',require_sources=True)['original_count']==5
print('  original frozen sources unchanged; 25 manifests and prior source pins PASS')
PYFINAL
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
echo 'T14 MACRO LAB SIGNED A SEMANTIC ORIGIN GATES ORIGINAL A1D ACCESS + REFERENCE P; ZERO NATIVE SPK LEARNING'
