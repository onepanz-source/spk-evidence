#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t10abc-def-ghi-cumulative.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T10 GATE FAIL CLOSED: REPORT_EXISTS' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-t10-p-provider-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/6] 19 cumulative manifests, source custody (12), frozen original SHA, parent report\n'
PYTHONPATH=. python3 - <<'PY'
import json
from pathlib import Path
from research.spk_v5_t10abc_def_ghi.cumulative_provider_gate import sha,PARENT,PE_SHA,BV_SHA
from research.spk_v5_t5mno import t5mno
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
 't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
 't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza',
 't9abc_def_ghi','t9jkl_mno_pqr','t9stu_vwx_yza','t10abc_def_ghi')
for name in names:
 p=Path('research')/('spk_v5_'+name)/'manifest.json'
 assert p.is_file() and not p.is_symlink(),'MISSING_MANIFEST '+name
 m=json.loads(p.read_bytes());assert m.get('promotion_allowed') is not True
 for rel,h in m['files'].items():
  f=Path(rel)
  assert f.is_file() and not f.is_symlink() and sha(f)==h,'SOURCE_SHA_DRIFT '+rel
 print('  PASS',name,len(m['files']))
assert sha('research/spk_v5_t10abc_def_ghi/reference/t9stu-vwx-yza-cumulative.json')==PARENT
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  original 12 sources and parent report PASS')
PY
printf '[2/6] Original frozen BV-v0e admission preflight (no substitute modules)\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
for c in (11,12):
 for g in (11,12):
  _,v=execute_raw(c,g)
  assert v['full_BV_scheduler'] and v['reverse_A_B_C'] and v['source_bv_deliveries']==2
_,v=execute_raw(12,11,drop_forward=True)
assert not v['reverse_A_B_C'] and v['source_bv_deliveries']==0
print('  genuine frozen scheduler admission preflight PASS')
PY
printf '[3/6] New T10 provider unit tests plus all 18 inherited cumulative suites\n'
for name in t10abc_def_ghi t9stu_vwx_yza t9jkl_mno_pqr t9abc_def_ghi t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[4/6] First cumulative provider report\n'
PYTHONPATH=. python3 -m research.spk_v5_t10abc_def_ghi.cumulative_provider_gate --root . --out "$TMP/first.json"
printf '[5/6] Second independent provider report, exact bytes and non-promotion\n'
PYTHONPATH=. python3 -m research.spk_v5_t10abc_def_ghi.cumulative_provider_gate --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
python3 - "$TMP/first.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));a,b,c=r['T10ABC'],r['T10DEF'],r['T10GHI']
s=b['reference_provider_scenarios'];w=c['negative_witness']
assert a['provider_called_in_actual_C_semantic_tick_store_write']
assert a['provider_veto_enforced_by_sqlite_UDF_trigger']
assert (s['fixed_control']['successes'],s['naive_three']['successes'],s['context_affinity']['successes'],s['serial']['successes'])==(48,84,88,88)
assert (s['naive_three']['waves'],s['context_affinity']['waves'],s['serial']['waves'])==(32,48,96)
assert (s['naive_three']['stale_vetoes'],s['context_affinity']['stale_vetoes'])==(4,0)
for n in ('naive_three','context_affinity','serial','restarted_affinity'):
 x=s[n];assert x['provider']['provider_v1_authorizations']==8
 assert x['provider']['provider_v1_commits']==8
 assert x['provider']['native_SPK_Memory_Contract_grants']==0
assert s['fixed_control']['provider']['provider_v1_authorizations']==0
assert s['context_affinity']['provider']==s['restarted_affinity']['provider']
assert all(w[k] for k in ('provider_denial_rollback_atomic','C_semantic_event_queued_after_denial','grant_and_P_absent_when_denied','reopen_restored_provider_and_single_commit','two_same_version_negative_votes_one_grant','native_port_denied'))
assert b['native_SPK_Memory_Contract_port']=='DENIED_NO_NATIVE_MEMORY_CONTRACT_PORT'
assert (r['native_SPK_P_grants'],r['native_SPK_P_writes'],r['native_BV_semantic_deliveries'],r['new_frozen_scheduler_calls'])==(0,0,0,0)
assert not r['native_learning'] and not r['promotion_allowed'] and r['host_can_forge']
print('  T10 provider veto, exact parity, restart & zero native adoption PASS')
PY
printf '[6/6] Freeze pin recheck and atomic evidence publication\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t10abc_def_ghi.cumulative_provider_gate import sha,PE_SHA,BV_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
PY
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
echo 'T10ABC/DEF/GHI REFERENCE TICK P ADMISSION PROVIDER PASS; 8 REFERENCE GRANTS; ZERO NATIVE SPK BV OR LEARNING'
