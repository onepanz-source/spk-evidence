#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t10jkl-mno-pqr-cumulative.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T10JKL GATE FAIL CLOSED: REPORT_EXISTS' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-t10-resource-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/6] Cumulative source manifest custody, original 12 source pins, T10 parent SHA\n'
PYTHONPATH=. python3 - <<'PY'
import json
from pathlib import Path
from research.spk_v5_t10jkl_mno_pqr.cumulative_resource_gate import sha,PARENT,PE_SHA,BV_SHA
from research.spk_v5_t5mno import t5mno
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
 't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
 't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza',
 't9abc_def_ghi','t9jkl_mno_pqr','t9stu_vwx_yza','t10abc_def_ghi','t10jkl_mno_pqr')
for name in names:
 p=Path('research')/('spk_v5_'+name)/'manifest.json'
 assert p.is_file() and not p.is_symlink(),'MISSING_MANIFEST '+name
 m=json.loads(p.read_bytes());assert m.get('promotion_allowed') is not True
 for rel,h in m['files'].items():
  f=Path(rel)
  assert f.is_file() and not f.is_symlink() and sha(f)==h,'SOURCE_SHA_DRIFT '+rel
 print('  PASS',name,len(m['files']))
assert sha('research/spk_v5_t10jkl_mno_pqr/reference/t10abc-def-ghi-cumulative.json')==PARENT
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  genuine 12 source pins and prior exact report PASS')
PY
printf '[2/6] Authentic original BV-v0e admission preflight (no local substitutes)\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
for c in (11,12):
 for g in (11,12):
  _,v=execute_raw(c,g)
  assert v['full_BV_scheduler'] and v['reverse_A_B_C'] and v['source_bv_deliveries']==2
_,v=execute_raw(12,11,drop_forward=True)
assert not v['reverse_A_B_C'] and v['source_bv_deliveries']==0
print('  frozen scheduler admission preflight PASS')
PY
printf '[3/6] New T10 resource tests + 19 inherited suites, fail closed\n'
for name in t10jkl_mno_pqr t10abc_def_ghi t9stu_vwx_yza t9jkl_mno_pqr t9abc_def_ghi t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[4/6] First T10 bounded P resource report\n'
PYTHONPATH=. python3 -m research.spk_v5_t10jkl_mno_pqr.cumulative_resource_gate --root . --out "$TMP/first.json"
printf '[5/6] Independent second report and exact-byte comparator\n'
PYTHONPATH=. python3 -m research.spk_v5_t10jkl_mno_pqr.cumulative_resource_gate --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
python3 - "$TMP/first.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));a,b,c=r['T10JKL'],r['T10MNO'],r['T10PQR'];s=b['scenarios'];w=c['negative_witness']
assert a['manifest_mode_execute_and_exact_C_P_scope'] and not a['original_memory_contract_source_loaded']
assert (s['fixed_control']['successes'],s['naive_three']['successes'],s['context_affinity']['successes'],s['serial']['successes'])==(48,84,88,88)
assert (s['naive_three']['waves'],s['context_affinity']['waves'],s['serial']['waves'])==(32,48,96)
assert (s['naive_three']['stale_vetoes'],s['context_affinity']['stale_vetoes'])==(4,0)
for name in ('naive_three','context_affinity','serial','restarted_affinity'):
 x=s[name];assert x['reference_grants']==x['reference_P_writes']==8
 assert x['resource']['total_consumed']==8 and x['resource']['native_SPK_memory_grants']==0
assert s['fixed_control']['resource']['total_consumed']==0
assert s['context_affinity']['resource']==s['restarted_affinity']['resource']
assert all(w.values())
assert c['native_seam_status']=='DENIED_NO_NATIVE_MEMORY_CONTRACT_PORT'
assert (r['native_SPK_P_grants'],r['native_SPK_P_writes'],r['native_BV_semantic_deliveries'])==(0,0,0)
assert not r['native_learning'] and not r['promotion_allowed'] and r['host_can_forge']
print('  reference P quota and native denial, restart, rollback and byte parity PASS')
PY
printf '[6/6] Recheck frozen pins; publish verified evidence once\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t10jkl_mno_pqr.cumulative_resource_gate import sha,PE_SHA,BV_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
PY
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
echo 'T10JKL/MNO/PQR BOUNDED P REFERENCE RESOURCE ADMISSION PASS; ZERO NATIVE SPK BV OR LEARNING'
