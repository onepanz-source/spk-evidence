#!/usr/bin/env bash
# SPK T6JKL/MNO/PQR CUMULATIVE: two peers, async/jitter/loss, conflicts/drift.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t6jkl-mno-pqr-cumulative.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo "T6JKL/MNO/PQR FAIL CLOSED: OUTPUT_EXISTS $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-t6jklmno-XXXXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/6] Manifest custody: eight inherited modules plus new cumulative milestone; pinned T6 report, PE/BV and 12 source files\n'
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
import hashlib,json
from research.spk_v5_t6jkl_mno_pqr.cumulative_gate_v0 import HISTORY_SHA,PE_SHA,BV_SHA
from research.spk_v5_t5mno import t5mno
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name in ('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx','t6abc_def_ghi','t6jkl_mno_pqr'):
    m=Path(f'research/spk_v5_{name}/manifest.json')
    assert m.is_file() and not m.is_symlink(), 'MISSING_MANIFEST_'+name
    o=json.loads(m.read_bytes())
    assert o.get('promotion_allowed') is not True and o.get('frozen_components_modified') is not True,'PROMOTION_DRIFT_'+name
    if name=='t6jkl_mno_pqr':
        assert o['promotion_allowed'] is False and o['native_learning'] is False and o['frozen_components_modified'] is False
    for path,expected in o['files'].items():
        p=Path(path)
        assert p.is_file() and not p.is_symlink(),'MISSING_FILE_'+path
        assert sha(p)==expected,'SHA_DRIFT_'+path
    print('  ',name,len(o['files']),'files verified')
assert sha('research/spk_v5_t6jkl_mno_pqr/reference/t6abc-def-ghi-functional-loop.json')==HISTORY_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  T6 pinned result, frozen PE, frozen scheduler, and all 12 original source pins OK')
PY
printf '[2/6] New asynchronous/multireceiver/adversarial tests and complete recent inherited research regressions\n'
for name in t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
    PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[3/6] First independent full research gate with byte-exact ancestral T6 replay\n'
PYTHONPATH=. python3 -m research.spk_v5_t6jkl_mno_pqr.cumulative_gate_v0 --root . --out "$TMP/one.json"
printf '[4/6] Second independent full research gate in a fresh Python process\n'
PYTHONPATH=. python3 -m research.spk_v5_t6jkl_mno_pqr.cumulative_gate_v0 --root . --out "$TMP/two.json"
cmp -- "$TMP/one.json" "$TMP/two.json"
printf '[5/6] Explicit causal, asynchronous and negative-boundary assertions\n'
python3 - "$TMP/one.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'));a=r['T6JKL'];b=r['T6MNO'];c=r['T6PQR']
assert r['ancestry_replayed_byte_exact'] and r['original_source_pins']==12
assert a['trials']==96 and a['receiver_nodes']==2 and a['phases']==4
assert a['control_joint_successes']==48 and a['trained_joint_successes']==80 and a['trained_success_delta']==32
assert a['per_phase_trained_successes']==[20,20,20,20] and a['policy_updates']==8 and a['matched_task_cues_and_goals']
assert not a['full_frozen_BV_scheduler_used']
assert b['reverse_order_successes']==80 and b['jitter_successes']==80 and b['jitter_control_successes']==48
assert b['jitter_seeds_0_through_9_joint_successes']==[80]*10
assert b['stale_policy_messages_rejected']==8 and b['nonfinalized_pending_decisions_closed']==8
assert b['bounded_loss_dropped_votes']==27 and b['bounded_loss_successes']==80 and b['bounded_loss_control_successes']==48
assert c['conflicting_receiver_judgments']==48 and c['conflict_scenario_updates']==4 and c['conflict_scenario_joint_successes']==40
assert c['no_feedback_updates']==0 and c['no_feedback_joint_successes']==48
assert c['overconstrained_budget_joint_successes']==44 and c['overconstrained_budget_policy_updates']==2
assert c['privileged_host_false_positive_pair_accepted'] and c['privileged_host_impersonated_D_accepted']
assert c['privileged_host_false_negative_pair_destabilized_C'] and not c['native_source_authentication']
assert r['host_can_forge'] and not r['A_sensor_authenticated'] and not r['D_sensor_authenticated']
assert r['native_BV_credit']==0 and r['native_learning'] is False and r['native_C_policy_modified'] is False
assert r['promotion_allowed'] is False and r['full_native_BV_scheduler_used'] is False
print('  Functional multi-receiver adaptation, bounded async, conflict abstention, negative budget and host forgery PASS')
PY
printf '[6/6] Seal new immutable deterministic report\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/one.json" "$OUT"
sha256sum -- "$OUT"
echo 'T6JKL/MNO/PQR CUMULATIVE MULTI-RECEIVER ASYNC MODEL ADAPTATION PASS; TWO SYNTHETIC RECEIVERS; HOST FORGEABLE; NO NATIVE BV OR LEARNING'
