#!/usr/bin/env bash
# SPK V5 T6ABC+T6DEF+T6GHI one cumulative gate, no frozen mutation.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t6abc-def-ghi-functional-loop.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo "T6 FAIL CLOSED: OUTPUT_EXISTS $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-v5-t6closedloop-XXXXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/6] Verify 8 cumulative manifests, latest pinned report and frozen 12-source custody\n'
PYTHONPATH=. python3 - <<'PYPIN'
from pathlib import Path
import hashlib,json
from research.spk_v5_t6abc_def_ghi.cumulative_gate_v0 import HISTORY_SHA, PE_SHA, BV_SHA
from research.spk_v5_t5mno import t5mno
for name in ('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx','t6abc_def_ghi'):
    m=Path(f'research/spk_v5_{name}/manifest.json')
    assert m.is_file() and not m.is_symlink(), 'MISSING_MANIFEST_'+name
    data=json.loads(m.read_bytes())
    assert data.get('promotion_allowed') is not True and data.get('frozen_components_modified') is not True,'MANIFEST_CONTRACT_'+name
    if name=='t6abc_def_ghi':
        assert data.get('promotion_allowed') is False and data.get('frozen_components_modified') is False
    for rel,expected in data['files'].items():
        p=Path(rel)
        assert p.is_file() and not p.is_symlink(),'MISSING_'+rel
        assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,'DRIFT_'+rel
    print('  ',name,len(data['files']),'pinned files OK')
assert hashlib.sha256(Path('research/spk_v5_t6abc_def_ghi/reference/t5pqr-stu-vwx-cumulative.json').read_bytes()).hexdigest()==HISTORY_SHA
assert hashlib.sha256(Path('spk_architecture_v1/pe_execution_v1b.py').read_bytes()).hexdigest()==PE_SHA
assert hashlib.sha256(Path('spk_backvalidation_v0/live_dual_scheduler_v0e.py').read_bytes()).hexdigest()==BV_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  frozen PE/BV and 12 original source SHA pins OK')
PYPIN
printf '[2/6] 3 research blocks: new tests plus every inherited T4ZABC-T5VWX regression\n'
for name in t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
    PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[3/6] Independent PE-fragment closed-loop, strict ancestor replay and causal ablation: run 1\n'
PYTHONPATH=. python3 -m research.spk_v5_t6abc_def_ghi.cumulative_gate_v0 --root . --out "$TMP/one.json"
printf '[4/6] Repeat complete audit in new Python process: run 2\n'
PYTHONPATH=. python3 -m research.spk_v5_t6abc_def_ghi.cumulative_gate_v0 --root . --out "$TMP/two.json"
printf '[5/6] Compare bytes and enforce source/credit/host adversarial limits\n'
cmp -- "$TMP/one.json" "$TMP/two.json"
python3 - "$TMP/one.json" <<'PYVERIFY'
import json,sys
r=json.load(open(sys.argv[1]));a=r['T6ABC'];d=r['T6DEF'];g=r['T6GHI']
assert r['ancestry_replay_byte_exact'] is True and r['original_source_pins']==12
assert a['real_frozen_PE_compute_function_reused'] is True and a['full_frozen_BV_scheduler_used'] is False
assert a['same_task_sequence'] is True and a['cases']==48
assert a['C_B_A_hops_per_trial']==a['A_B_C_feedback_round_trips_per_trial']==48
assert d['baseline_successes']==0 and d['learning_successes']==46 and d['success_improvement']==46
assert d['learning_policy_updates']==2 and d['baseline_policy_updates']==0
assert d['first_change_after_feedback'] is True
assert g['model_only_forced_alternative_trials']==48 and g['learning_counterfactual_total_difference']==44
assert g['baseline_counterfactual_total_difference']==-48 and g['no_C_signal_in_control_world'] is True
assert g['feedback_absence_maintains_policy'] and g['feedback_delay_at_deadline_accepted']
assert len(g['invalid_feedback_rejected'])==8 and set(g['invalid_feedback_rejected'].values())=={'REJECTED'}
assert g['host_forged_fresh_A_ledger_accepted'] and g['host_can_destabilize_learning_by_fake_negative']
assert r['experimental_shadow_C_policy_updated'] is True
assert r['native_C_policy_modified'] is False and r['native_BV_credit']==0 and r['native_learning'] is False
assert r['real_world_causal_identifiability'] is False and r['host_can_forge'] is True
assert r['promotion_allowed'] is False and r['A_sensor_authenticated'] is False and r['C_source_authenticated'] is False
print('  T6ABC/DEF/GHI functional adaptation + model-only ablation + 8 rejections + host counterexample PASS')
PYVERIFY
printf '[6/6] Seal deterministic immutable research report\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/one.json" "$OUT"
sha256sum -- "$OUT"
echo 'T6ABC/DEF/GHI CUMULATIVE FUNCTIONAL PE-FRAGMENT ADAPTATION PASS; MODEL-ONLY CAUSALITY; HOST FORGERY STILL POSSIBLE; NO NATIVE BV OR LEARNING'
