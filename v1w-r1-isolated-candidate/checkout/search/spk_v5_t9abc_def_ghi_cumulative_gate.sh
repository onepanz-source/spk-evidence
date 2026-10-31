#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t9abc-def-ghi-cumulative.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T9 CONCURRENCY FAIL CLOSED: REPORT_EXISTS' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-t9-gate-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/6] All 16 cumulative SHA manifests, 12 original source pins, frozen PE/BV\n'
PYTHONPATH=. python3 - <<'PY'
import json
from pathlib import Path
from research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate import sha,PARENT_SHA,PE_SHA,BV_SHA
from research.spk_v5_t5mno import t5mno
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
 't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
 't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza','t9abc_def_ghi')
for n in names:
 p=Path('research')/f'spk_v5_{n}'/'manifest.json'
 assert p.is_file() and not p.is_symlink(),'MISSING_MANIFEST '+n
 m=json.loads(p.read_bytes());assert m.get('promotion_allowed') is not True
 for rel,want in m['files'].items():
  f=Path(rel);assert f.is_file() and not f.is_symlink() and sha(f)==want,'MANIFEST_DRIFT '+rel
 print('  PASS',n,len(m['files']))
assert sha('research/spk_v5_t9abc_def_ghi/reference/t8stu-vwx-yza.json')==PARENT_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  12 original source files + two frozen code pins PASS')
PY
printf '[2/6] Genuine BV-v0e admission preflight (no local substitutes)\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
for c in (11,12):
 for g in (11,12):
  _,v=execute_raw(c,g)
  assert v['full_BV_scheduler'] and v['reverse_A_B_C'] and v['source_bv_deliveries']==2
_,v=execute_raw(12,11,drop_forward=True)
assert not v['reverse_A_B_C'] and v['source_bv_deliveries']==0
print('  five genuine source admission cases PASS')
PY
printf '[3/6] New concurrency suite and inherited regressions (one grouped gate)\n'
for name in t9abc_def_ghi t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[4/6] First full reference report\n'
PYTHONPATH=. python3 -m research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate --root . --out "$TMP/first.json"
printf '[5/6] Second independent report and negative-gate verification\n'
PYTHONPATH=. python3 -m research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
python3 - "$TMP/first.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1])); a=r['T9ABC'];b=r['T9DEF'];c=r['T9GHI']
assert (a['serial_t8_parity']['successes'],a['two_epoch_adaptive']['successes'],
        a['three_epoch_adaptive']['successes'],a['three_epoch_control']['successes'])==(88,88,84,48)
assert (a['three_epoch_adaptive']['grants'],a['three_epoch_adaptive']['vetoes'])==(8,4)
assert a['three_epoch_no_feedback']['grants']==0
assert b['same_version_CAS_and_context_independence']['two_same_version_negative_votes_one_grant']
assert b['crash_resume']['replay_safe']
assert c['resource_admission']['active_epoch_capacity_denied']
assert c['fifo_fairness']['late_episode_settled']
assert not r['native_learning'] and not r['promotion_allowed'] and r['host_can_forge']
assert (r['native_SPK_P_grants'],r['native_BV_semantic_deliveries'],
        r['new_original_BV_scheduler_calls'])==(0,0,0)
print('  concurrent CAS, FIFO and reference/native boundary PASS')
PY
printf '[6/6] Frozen pins recheck and atomic evidence publication\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t9abc_def_ghi.cumulative_concurrency_gate import sha,PE_SHA,BV_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
PY
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
echo 'T9ABC/DEF/GHI CONCURRENT V1 REFERENCE CAS/FAIRNESS PASS; RESEARCH ONLY; ZERO NATIVE SPK LEARNING'
