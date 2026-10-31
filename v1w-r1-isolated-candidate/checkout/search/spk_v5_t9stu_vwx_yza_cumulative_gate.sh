#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t9stu-vwx-yza-cumulative.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T9STU GATE FAIL CLOSED: REPORT_EXISTS' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-t9stu-gate-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/6] 18 cumulative manifests, original 12 source pins, and parent SHA\n'
PYTHONPATH=. python3 - <<'PY'
import json
from pathlib import Path
from research.spk_v5_t9stu_vwx_yza.cumulative_p_boundary_gate import sha,PARENT,PE_SHA,BV_SHA
from research.spk_v5_t5mno import t5mno
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
 't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
 't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza',
 't9abc_def_ghi','t9jkl_mno_pqr','t9stu_vwx_yza')
for name in names:
 p=Path('research')/f'spk_v5_{name}'/'manifest.json'
 assert p.is_file() and not p.is_symlink(),'MISSING_MANIFEST '+name
 m=json.loads(p.read_bytes())
 assert m.get('promotion_allowed') is not True
 for rel,h in m['files'].items():
  f=Path(rel)
  assert f.is_file() and not f.is_symlink() and sha(f)==h,'SHA_MANIFEST_DRIFT '+rel
 print('  PASS',name,len(m['files']))
assert sha('research/spk_v5_t9stu_vwx_yza/reference/t9jkl-mno-pqr-cumulative.json')==PARENT
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  source custody and reference report PASS')
PY
printf '[2/6] Genuine frozen BV-v0e admission preflight (no substitute modules)\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
for c in (11,12):
 for g in (11,12):
  _, v=execute_raw(c,g)
  assert v['full_BV_scheduler'] and v['reverse_A_B_C'] and v['source_bv_deliveries']==2
_,v=execute_raw(12,11,drop_forward=True)
assert not v['reverse_A_B_C'] and v['source_bv_deliveries']==0
print('  original source scheduler admission PASS')
PY
printf '[3/6] New reference P-boundary suite + all inherited cumulative regressions\n'
for name in t9stu_vwx_yza t9jkl_mno_pqr t9abc_def_ghi t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[4/6] First independent P-store boundary report\n'
PYTHONPATH=. python3 -m research.spk_v5_t9stu_vwx_yza.cumulative_p_boundary_gate --root . --out "$TMP/first.json"
printf '[5/6] Second report, byte-exact comparison, and non-promotion guards\n'
PYTHONPATH=. python3 -m research.spk_v5_t9stu_vwx_yza.cumulative_p_boundary_gate --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
python3 - "$TMP/first.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));s=r['T9STU'];t=r['T9VWX'];u=r['T9YZA']
a,b,c=s['fenced_naive'],s['fenced_affinity'],s['fenced_serial']
assert (a['successes'],b['successes'],c['successes'],u['fixed_control']['successes'])==(84,88,88,48)
assert (a['waves'],b['waves'],c['waves'])==(32,48,96)
assert (a['reference_P_grants'],b['reference_P_grants'],c['reference_P_grants'])==(8,8,8)
assert (a['stale_vetoes'],b['stale_vetoes'])==(4,0)
assert a['custody']['verified_reference_grants']==8
assert t['native_target_admission']=='DENIED_NO_NATIVE_MEMORY_CONTRACT_PORT'
assert not t['native_memory_contract_port_implemented']
assert u['negative_witness']['privileged_host_can_reseal']
assert (r['native_SPK_P_grants'],r['native_SPK_P_writes'],r['native_BV_semantic_deliveries'],r['new_frozen_scheduler_calls'])==(0,0,0,0)
assert not r['native_learning'] and not r['promotion_allowed'] and r['host_can_forge']
print('  store-side fence, causal lineage, native non-promotion PASS')
PY
printf '[6/6] Frozen pin recheck and atomic report publication\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t9stu_vwx_yza.cumulative_p_boundary_gate import sha,PE_SHA,BV_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
PY
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
echo 'T9STU/VWX/YZA REFERENCE P STORE FENCE / CUSTODY / NATIVE SEAM RESEARCH PASS; ZERO NATIVE SPK LEARNING'
