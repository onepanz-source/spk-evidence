#!/usr/bin/env bash
# One cumulative T7 gate: full frozen BV per episode, research-owned durable P.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t7abc-def-ghi-bv-epoch-bridge.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo "T7 FAIL CLOSED: REPORT_EXISTS $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-t7-bv-epoch-XXXXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] Verify eleven cumulative manifests and original frozen-source custody\n'
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
import hashlib,json
from research.spk_v5_t7abc_def_ghi.cumulative_gate_v0 import PRIOR_SHA,BV_SHA,PE_SHA
from research.spk_v5_t5mno import t5mno
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
for name in ('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno',
             't5pqr_stu_vwx','t6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza','t7abc_def_ghi'):
    mf=Path(f'research/spk_v5_{name}/manifest.json')
    assert mf.is_file() and not mf.is_symlink(), 'MISSING_MANIFEST_'+name
    manifest=json.loads(mf.read_bytes())
    assert manifest.get('promotion_allowed') is not True and manifest.get('native_learning') is not True
    for rel,expected in manifest['files'].items():
        p=Path(rel)
        assert p.is_file() and not p.is_symlink() and sha(p)==expected,'SOURCE_SHA_DRIFT:'+rel
    print('  manifest',name,len(manifest['files']),'files')
assert sha('research/spk_v5_t7abc_def_ghi/reference/t6stu-vwx-yza-cumulative.json')==PRIOR_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  original sources: 12 pins verified')
PY
printf '[2/8] Actual frozen scheduler preflight on A/B/C cases (no stubs)\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import execute_episode
import spk_backvalidation_v0.live_dual_scheduler_v0e as original
from pathlib import Path
assert Path(original.__file__).resolve()==Path('spk_backvalidation_v0/live_dual_scheduler_v0e.py').resolve()
for choice in (11,12):
    for goal in (11,12):
        x=execute_episode(choice,goal)
        assert x['full_BV_scheduler'] and x['C_B_A'] and x['reverse_A_B_C']
        assert x['A_outcome']==('IMPROVED' if choice==goal else 'WORSENED')
        assert x['source_batches']==3 and x['source_bv_deliveries']==2
assert execute_episode(12,11,drop_forward=True)['A_outcome']=='ABSENT'
print('  5 real unchanged BV-v0e source executions, one A receiver, PE-C/B/A PASS')
PY
printf '[3/8] 30 new source, owned-P, adversarial and recovery tests\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t7abc_def_ghi/tests -q
printf '[4/8] 270 inherited local research regression tests\n'
for name in t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
    PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[5/8] First strict full-BV 361-epoch run with persistent owned-C P-state\n'
PYTHONPATH=. python3 -m research.spk_v5_t7abc_def_ghi.cumulative_gate_v0 --root . --out "$TMP/one.json"
printf '[6/8] Second independent full-BV 361-epoch run; byte-exact report parity\n'
PYTHONPATH=. python3 -m research.spk_v5_t7abc_def_ghi.cumulative_gate_v0 --root . --out "$TMP/two.json"
cmp -- "$TMP/one.json" "$TMP/two.json"
printf '[7/8] Fail-closed interpretation, causal boundary and frozen files unchanged\n'
python3 - "$TMP/one.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf8'))
a=r['T7ABC'];d=r['T7DEF'];n=r['T7GHI']
assert a['genuine_frozen_BV_executions']==361
assert a['three_node_bound'] and a['same_epoch_A_terminal_assessment_and_C_receipt']
assert a['BV_packet_contains_A_semantic_verdict'] is False and a['A_emits_semantic_output_separately']
assert a['control_96']['successful_A_assessments']==48 and a['adaptive_96']['successful_A_assessments']==88
assert a['control_96']['P_updates']==0 and a['adaptive_96']['P_updates']==8
assert a['adaptive_96']['structural_BV_C_deliveries']==96
assert d['adaptive_improvement_96']==40 and d['stationary_24']=={'control':0,'adaptive':22}
assert d['recover']['one_update_after_reopen'] and d['recover']['duplicate_after_reopen_rejected']
assert n['lost_forward_24']['structural_BV_C_deliveries']==0
assert n['lost_forward_24']['P_updates']==0
assert n['host_forgery_witness']['host_forged_ledger_accepted']
assert r['host_can_forge'] and not r['native_learning'] and not r['native_C_authenticated']
assert r['native_BV_credit']==0 and not r['promotion_allowed'] and not r['native_P_state_modified']
print('  genuine frozen BV scheduler + research state, not native learning, PASS')
PY
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7abc_def_ghi.cumulative_gate_v0 import PE_SHA,BV_SHA,sha_file
assert sha_file('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha_file('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
print('  frozen source bytes remain identical')
PY
printf '[8/8] Publish once and verify evidence file SHA-256\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/one.json" "$OUT"
sha256sum -- "$OUT"
echo 'T7ABC/DEF/GHI CUMULATIVE FROZEN BV-V0E EPOCH ADAPTER RESEARCH PASS; A SEMANTIC OUTCOME SIDECAR; EXTERNAL C P; HOST FORGEABLE; NO NATIVE BV OR LEARNING'
