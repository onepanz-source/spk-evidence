#!/usr/bin/env bash
# T8 V1 CANDIDATE schema/authority compatibility research. Native adoption: NONE.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t8abc-def-ghi-cumulative.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo 'T8 FAIL CLOSED: REPORT_EXISTS' >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-t8-v1-contracts-XXXXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/7] Pin manifest, prior report, original BV/PE and 12 source refs\n'
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
import hashlib,json
from research.spk_v5_t8abc_def_ghi.cumulative_gate_v0 import sha,T7_REF_SHA,PE_SHA,BV_SHA
from research.spk_v5_t5mno import t5mno
for name in ('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx',
             't6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi',
             't7jkl_mno_pqr','t8abc_def_ghi'):
  p=Path(f'research/spk_v5_{name}/manifest.json')
  assert p.is_file() and not p.is_symlink(),'MISSING_MANIFEST '+name
  m=json.loads(p.read_bytes());assert m.get('promotion_allowed') is not True
  for rel,h in m['files'].items():
    file=Path(rel);assert file.is_file() and not file.is_symlink() and sha(file)==h,'SOURCE_DRIFT '+rel
  print('  verified',name,len(m['files']))
assert sha('research/spk_v5_t8abc_def_ghi/reference/t7jkl-mno-pqr.json')==T7_REF_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  frozen code and 12 original source pins verified')
PY
printf '[2/7] Genuine frozen BV scheduler preflight, original admission dependencies\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
for choice in (11,12):
  for goal in (11,12):
    source,e=execute_raw(choice,goal)
    assert e['full_BV_scheduler'] and e['reverse_A_B_C'] and e['source_bv_deliveries']==2
    assert e['A_outcome']==('IMPROVED' if choice==goal else 'WORSENED')
print('  4 authentic PE/BV epoch preflights PASS')
PY
printf '[3/7] Candidate v1 unit, negative tests and inherited regressions\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t8abc_def_ghi/tests -q
for name in t7jkl_mno_pqr t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
    PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[4/7] Full T8 comparison, real BV-v0e scheduler, candidate schema + P dry run\n'
PYTHONPATH=. python3 -m research.spk_v5_t8abc_def_ghi.cumulative_gate_v0 --root . --out "$TMP/first.json"
printf '[5/7] Independent rerun, byte-for-byte deterministic\n'
PYTHONPATH=. python3 -m research.spk_v5_t8abc_def_ghi.cumulative_gate_v0 --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
printf '[6/7] Validate bounded 48/88 parity, zero native grants and host forgery\n'
python3 - "$TMP/first.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['original_scheduler_calls']==216
assert r['T8GHI']['baseline_96']['successes']==48
assert r['T8GHI']['adaptive_96']['successes']==88
assert r['T8GHI']['adaptive_96']['updates']==8
assert r['T8GHI']['dropped_forward_24']['updates']==0
assert r['T8DEF']['native_admission_success_count']==0
assert r['T8DEF']['native_P_updates']==0
assert r['T8GHI']['privileged_host_counterexample']['new_real_scheduler_calls']==0
assert r['T8GHI']['privileged_host_counterexample']['research_P_changed']
assert not r['T8GHI']['privileged_host_counterexample']['native_P_changed']
assert r['host_can_forge'] and not r['native_learning'] and not r['promotion_allowed']
assert r['native_semantic_BV_credit']==0 and not r['native_P_state_modified']
print('  candidate-only claims + hostile host negative witness PASS')
PY
printf '[7/7] Publish one report after final original BV/PE SHA check\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t8abc_def_ghi.cumulative_gate_v0 import sha,PE_SHA,BV_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
PY
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
echo 'T8ABC/DEF/GHI CUMULATIVE V1 CANDIDATE SEMANTIC AND P ADMISSION RESEARCH PASS; ZERO NATIVE GRANTS; HOST FORGEABLE; NO NATIVE LEARNING'
