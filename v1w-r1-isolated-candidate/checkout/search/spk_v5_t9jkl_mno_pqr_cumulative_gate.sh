#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t9jkl-mno-pqr-cumulative.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T9JKL GATE FAIL CLOSED: REPORT_EXISTS' >&2; exit 3; }
TMP="$(mktemp -d /tmp/spk-t9jkl-gate-XXXXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/6] Cumulative 17 manifests, frozen pins, and 12 original source files\n'
PYTHONPATH=. python3 - <<'PY'
import json
from pathlib import Path
from research.spk_v5_t9jkl_mno_pqr.cumulative_evidence_frontier import sha,PARENT_SHA,PE_SHA,BV_SHA
from research.spk_v5_t5mno import t5mno
names=('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
 't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
 't7jkl_mno_pqr','t8abc_def_ghi','t8jkl_mno_pqr','t8stu_vwx_yza',
 't9abc_def_ghi','t9jkl_mno_pqr')
for n in names:
 p=Path('research')/f'spk_v5_{n}'/'manifest.json'
 assert p.is_file() and not p.is_symlink(),'MISSING_MANIFEST '+n
 m=json.loads(p.read_bytes());assert m.get('promotion_allowed') is not True
 for rel,want in m['files'].items():
  f=Path(rel)
  assert f.is_file() and not f.is_symlink() and sha(f)==want,'MANIFEST_DRIFT '+rel
 print('  PASS',n,len(m['files']))
assert sha('research/spk_v5_t9jkl_mno_pqr/reference/t9abc-def-ghi-cumulative.json')==PARENT_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  source custody & frozen pins PASS')
PY
printf '[2/6] Source BV-v0e admission preflight (no substitute modules)\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
for c in (11,12):
 for g in (11,12):
  _,v=execute_raw(c,g)
  assert v['full_BV_scheduler'] and v['reverse_A_B_C'] and v['source_bv_deliveries']==2
_,v=execute_raw(12,11,drop_forward=True)
assert not v['reverse_A_B_C'] and v['source_bv_deliveries']==0
print('  five authentic original scheduler cases PASS')
PY
printf '[3/6] New T9 evidence/admission suite + all grouped inherited suites\n'
for name in t9jkl_mno_pqr t9abc_def_ghi t8stu_vwx_yza t8jkl_mno_pqr t8abc_def_ghi t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
 PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[4/6] First evidence-and-admission cumulative report\n'
PYTHONPATH=. python3 -m research.spk_v5_t9jkl_mno_pqr.cumulative_evidence_frontier --root . --out "$TMP/first.json"
printf '[5/6] Second independent report, byte compare, and fail-closed research boundary\n'
PYTHONPATH=. python3 -m research.spk_v5_t9jkl_mno_pqr.cumulative_evidence_frontier --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
python3 - "$TMP/first.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
a,b,c=r['T9JKL'],r['T9MNO'],r['T9PQR']
assert (b['serial']['successes'],b['naive_three_inflight']['successes'],b['context_affinity']['successes'],b['fixed_control']['successes'])==(88,84,88,48)
assert (b['naive_three_inflight']['waves'],b['context_affinity']['waves'])==(32,48)
assert (a['historical_veto_receipts'],a['historical_feedback_P_grants'],b['context_affinity']['stale_vetoes'])==(4,0,0)
assert (b['context_affinity']['P_grants'],b['naive_three_inflight']['P_grants'])==(8,8)
assert c['stale_credit_harm_counterexample']['unsafe_A_PE_verdict']=='WORSENED'
assert c['restarted_naive']['core_rows_digest']==b['naive_three_inflight']['core_rows_digest']
assert not c['credit_reinterpretation_permitted'] and r['host_can_forge'] and not r['promotion_allowed']
assert (r['native_SPK_P_grants'],r['native_BV_semantic_deliveries'],r['new_frozen_scheduler_calls'])==(0,0,0)
assert not r['native_learning']
print('  historical-credit, admission frontier and negative boundary PASS')
PY
printf '[6/6] Recheck source pins and publish report atomically\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t9jkl_mno_pqr.cumulative_evidence_frontier import sha,PE_SHA,BV_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
PY
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
echo 'T9JKL/MNO/PQR HISTORICAL STALE CREDIT & ADMISSION FRONTIER RESEARCH PASS; ZERO NATIVE BV OR LEARNING'
