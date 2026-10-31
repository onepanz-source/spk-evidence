#!/usr/bin/env bash
# SPK V5 cumulative T5PQR/STU/VWX: ONE gate for several related research stages.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t5pqr-stu-vwx-cumulative.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo "T5 CUMULATIVE FAIL CLOSED: OUTPUT_EXISTS $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-v5-t5-cumulative-XXXXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/6] Seven additive manifests plus pinned original 12-source SHA custody\n'
PYTHONPATH=. python3 - <<'PYMANIFEST'
import hashlib,json
from pathlib import Path
from research.spk_v5_t5mno import t5mno
for name in ('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx'):
    manifest=Path(f'research/spk_v5_{name}/manifest.json')
    if not manifest.is_file() or manifest.is_symlink():
        raise SystemExit('T5 CUMULATIVE FAIL CLOSED: missing manifest '+str(manifest))
    m=json.loads(manifest.read_bytes())
    if m.get('promotion_allowed') is True or m.get('frozen_components_modified') is True:
        raise SystemExit('T5 CUMULATIVE FAIL CLOSED: invalid contract flags '+str(manifest))
    for relative,expected in m['files'].items():
        path=Path(relative)
        if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise SystemExit('T5 CUMULATIVE FAIL CLOSED: SHA drift '+relative)
    print('  ',name,'file-pins',len(m['files']),'PASS')
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  original 12 source SHA pins PASS')
PYMANIFEST
printf '[2/6] Cumulative new causal, intervention, feedback, attack tests + inherited regressions\n'
for name in t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
    PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[3/6] Independent research audit 1: 180 prior A observations; 24 paired trials and 24 A-B-C feedbacks\n'
PYTHONPATH=. python3 -m research.spk_v5_t5pqr_stu_vwx.cumulative_gate_v0 --root . --out "$TMP/one.json"
printf '[4/6] Independent research audit 2: repeat complete pipeline from pinned sources\n'
PYTHONPATH=. python3 -m research.spk_v5_t5pqr_stu_vwx.cumulative_gate_v0 --root . --out "$TMP/two.json"
printf '[5/6] Byte-exact determinism, attack counterexamples and strict NO-PROMOTION gate\n'
cmp -- "$TMP/one.json" "$TMP/two.json"
python3 - "$TMP/one.json" <<'PYVERIFY'
import json,sys
v=json.load(open(sys.argv[1]));p=v['T5PQR'];s=v['T5STU'];w=v['T5VWX']
assert v['T5MNO_reexecuted_byte_exact'] is True and v['original_source_pin_count']==12
assert p['cases']==180 and p['two_opposed_causal_worlds_fit_all_observed_data'] is True
assert p['world_illustrative_effects']==[1,-1] and p['real_C_effect_identifiable_from_T5MNO'] is False
assert s['model_only_twin_trials']==24 and s['simulated_arms']==48 and s['model_effect_counts']=={'-1':8,'0':8,'2':8}
assert s['simulated_paired_effect_numerator']==8 and s['simulated_paired_effect_denominator']==24
assert s['native_C_interventions']==0 and s['authenticated_sensor_observations']==0 and s['real_C_effect_identified'] is False
assert w['research_A_feedback_messages']==w['B_relay_messages']==w['C_receiver_messages']==24
assert w['C_receiver_outcomes']=={'IMPROVED':8,'UNCHANGED':8,'WORSENED':8}
assert len(w['negative_attacks'])==6 and set(w['negative_attacks'].values())=={'REJECTED'}
assert w['host_reconstructed_fresh_ledger_accepted'] is True
assert w['host_reconstructed_C_feedback_sha256']!=w['C_feedback_sha256']
assert w['C_native_credit_applied']==w['C_native_learning_steps']==0
assert v['new_original_BV_scheduler_calls']==v['new_original_PE_compute_calls']==0
assert v['C_native_authority_authenticated'] is False and v['A_sensor_authenticated'] is False
assert v['real_C_causal_attribution_proven'] is False and v['native_BV_credit']==0
assert v['native_learning'] is False and v['promotion_allowed'] is False
print('  THREE CUMULATIVE GATES PASS; 6 ATTACKS REJECTED; HOST COUNTERFEIT STILL ACCEPTED; 0 NATIVE BV')
PYVERIFY
printf '[6/6] Seal one combined report and print checksum\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/one.json" "$OUT"
sha256sum -- "$OUT"
echo 'T5PQR/STU/VWX CUMULATIVE RESEARCH PASS; OBSERVATIONAL CAUSALITY NOT IDENTIFIABLE; SYNTHETIC TRIALS ONLY; SHADOW FEEDBACK NOT NATIVE BV OR LEARNING'
