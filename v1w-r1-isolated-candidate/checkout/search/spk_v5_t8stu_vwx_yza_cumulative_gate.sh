#!/usr/bin/env bash
# T8STU/VWX/YZA: v1 integrated event ticks reference, not native SPK learning.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t8stu-vwx-yza-cumulative.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T8 V1 TICK GATE FAIL CLOSED: REPORT_EXISTS' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-v1tick-gate-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/6] SHA-pinned 15 incremental manifests, original 12 source files and frozen code\n'
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
import json
from research.spk_v5_t8stu_vwx_yza.cumulative_tick_gate import sha,PE_SHA,BV_SHA,PREVIOUS_SHA
from research.spk_v5_t5mno import t5mno
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
    't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
    't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza')
for name in names:
    p=Path('research')/f'spk_v5_{name}'/'manifest.json'
    assert p.is_file() and not p.is_symlink(),'MISSING_MANIFEST '+name
    m=json.loads(p.read_bytes())
    assert m.get('promotion_allowed') is not True
    for file,h in m['files'].items():
        f=Path(file)
        assert f.is_file() and not f.is_symlink() and sha(f)==h,'SOURCE_PIN_MISMATCH '+file
    print('  PASS',name,len(m['files']))
assert sha('research/spk_v5_t8stu_vwx_yza/reference/t8jkl-mno-pqr.json')==PREVIOUS_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  12 original file pins + 2 frozen sources + prior report PASS')
PY
printf '[2/6] Five authentic BV-v0e admission preflight executions (no stubs)\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
for c in (11,12):
 for g in (11,12):
  raw,ev=execute_raw(c,g)
  assert ev['full_BV_scheduler'] and ev['reverse_A_B_C'] and ev['source_bv_deliveries']==2
raw,ev=execute_raw(12,11,drop_forward=True)
assert not ev['reverse_A_B_C'] and ev['source_bv_deliveries']==0
print('  original BV-v0e genuine admission PASS')
PY
printf '[3/6] New V1 tick/semantic/P tests and entire inherited milestone regression\n'
for name in t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
    PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[4/6] Independently re-execute full BV-v0e oracle 216 episodes + new tick engine\n'
PYTHONPATH=. python3 -m research.spk_v5_t8stu_vwx_yza.cumulative_tick_gate --root . --out "$TMP/first.json"
printf '[5/6] Independent rerun, exact parity and fail-closed acceptance\n'
PYTHONPATH=. python3 -m research.spk_v5_t8stu_vwx_yza.cumulative_tick_gate --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
python3 - "$TMP/first.json" <<'PY'
import sys,json
r=json.load(open(sys.argv[1]))
t=r['T8STU'];a=t['adaptive_96'];b=t['baseline_96'];d=t['lost_forward_24']
assert (a['successes'],b['successes'],d['successes'])==(88,48,0)
assert (a['reference_tick_P_grants'],b['reference_tick_P_grants'],d['reference_tick_P_grants'])==(8,0,0)
assert (a['semantic_receipts'],b['semantic_receipts'],d['semantic_receipts'])==(96,96,0)
assert (a['source_oracle_calls'],b['source_oracle_calls'],d['source_oracle_calls'])==(96,96,24)
assert a['reference_tick_events_executed']==480
assert r['T8VWX']['recovery']['replay_did_not_reapply'] and r['T8VWX']['deadline']['tick_19_denied_P']
assert r['T8YZA']['host_goal_control_counterexample']['host_can_drive_reference_grant']
assert r['native_SPK_P_grants']==r['native_SPK_P_writes']==r['native_BV_semantic_deliveries']==0
assert not r['native_learning'] and not r['promotion_allowed'] and r['host_can_forge']
assert r['T8VWX']['parity_to_T8_full_frozen_source_sha'] is True
print('  V1 tick-grant integration / negative boundaries / frozen parity PASS')
PY
printf '[6/6] Verify frozen file integrity once more; publish one cumulative evidence file\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t8stu_vwx_yza.cumulative_tick_gate import sha,PE_SHA,BV_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
PY
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
echo 'T8STU/VWX/YZA V1 INTEGRATED TICK REFERENCE PASS; 8 REFERENCE TICK GRANTS; ZERO NATIVE SPK BV OR LEARNING'
