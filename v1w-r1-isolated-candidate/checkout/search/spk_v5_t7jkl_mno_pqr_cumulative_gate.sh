#!/usr/bin/env bash
# Fail-closed additive research checkpoint, native original scheduler preflight.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t7jkl-mno-pqr-cumulative.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo "T7JKL/MNO/PQR FAIL CLOSED: REPORT_EXISTS $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-t7jkl-semantic-XXXXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/8] Verify 12 research manifests, pinned original source and frozen PE/BV\n'
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
import hashlib,json
from research.spk_v5_t7jkl_mno_pqr.cumulative_gate_v0 import REFERENCE_SHA,PE_SHA,BV_SHA
from research.spk_v5_t5mno import t5mno
sha=lambda x:hashlib.sha256(Path(x).read_bytes()).hexdigest()
for name in ('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno',
             't5pqr_stu_vwx','t6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza',
             't7abc_def_ghi','t7jkl_mno_pqr'):
    mf=Path(f'research/spk_v5_{name}/manifest.json')
    assert mf.is_file() and not mf.is_symlink(),'MISSING_MANIFEST:'+name
    manifest=json.loads(mf.read_bytes())
    assert manifest.get('promotion_allowed') is not True and manifest.get('native_learning') is not True
    for rel,expected in manifest['files'].items():
        p=Path(rel)
        assert p.is_file() and not p.is_symlink() and sha(p)==expected, 'SHA_DRIFT:'+rel
    print('  verified',name,len(manifest['files']),'files')
assert sha('research/spk_v5_t7jkl_mno_pqr/reference/t7abc-def-ghi.json')==REFERENCE_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  original-source custody: 12 pins; frozen PE/BV exact')
PY
printf '[2/8] Five actual frozen BV-v0e source preflight cases, no admission substitutes\n'
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7jkl_mno_pqr.native_epoch_v0 import execute_raw
import spk_backvalidation_v0.live_dual_scheduler_v0e as original
from pathlib import Path
assert Path(original.__file__).resolve()==Path('spk_backvalidation_v0/live_dual_scheduler_v0e.py').resolve()
for choice in (11,12):
  for goal in (11,12):
    src,e=execute_raw(choice,goal)
    assert e['full_BV_scheduler'] and e['A_outcome']==('IMPROVED' if choice==goal else 'WORSENED')
    assert e['C_B_A'] and e['reverse_A_B_C'] and e['source_bv_deliveries']==2
src,e=execute_raw(12,11,drop_forward=True)
assert e['A_outcome']=='ABSENT' and e['source_bv_deliveries']==0
print('  real BV-v0e and original admission preflight PASS')
PY
printf '[3/8] 34 new tests including source tamper, semantic chain, P-version and host forgery\n'
PYTHONPATH=. python3 -m unittest discover -s research/spk_v5_t7jkl_mno_pqr/tests -q
printf '[4/8] 300 inherited regressions, from T4ZABC through T7ABC\n'
for name in t7abc_def_ghi t6stu_vwx_yza t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
    PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[5/8] First full frozen BV + semantic receipt + research P transaction execution\n'
PYTHONPATH=. python3 -m research.spk_v5_t7jkl_mno_pqr.cumulative_gate_v0 --root . --out "$TMP/first.json"
printf '[6/8] Second independent run and byte-exact reproducibility\n'
PYTHONPATH=. python3 -m research.spk_v5_t7jkl_mno_pqr.cumulative_gate_v0 --root . --out "$TMP/second.json"
cmp -- "$TMP/first.json" "$TMP/second.json"
printf '[7/8] Validate no native promotion and counterexample from coherent forged source\n'
python3 - "$TMP/first.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf8'))
a,b,c=r['T7JKL'],r['T7MNO'],r['T7PQR']
assert a['original_frozen_scheduler_calls']==217
assert a['control_96']['successes']==48 and a['adaptive_96']['successes']==88
assert a['adaptive_96']['P_updates']==8 and a['control_96']['P_updates']==0
assert not a['native_BV_packet_semantic'] and a['A_B_C_semantic_overlay_only']
assert b['persisted_model_improvement']==40 and not b['native_memory_contract_admission']
assert b['restart_once_and_replay_reject']['replay_denied']
assert c['dropped_forward_24']['forward_deliveries']==0
assert c['dropped_forward_24']['P_updates']==0
assert c['privileged_host_full_source_rebinding']['new_original_scheduler_calls']==0
assert c['privileged_host_full_source_rebinding']['forged_research_P_intent_committed']
assert r['host_can_forge'] and not r['native_learning'] and not r['native_P_state_modified']
assert r['native_BV_credit']==0 and not r['promotion_allowed']
print('  research P / native BV structural boundary, hostile-host counterexample PASS')
PY
PYTHONPATH=. python3 - <<'PY'
from research.spk_v5_t7jkl_mno_pqr.cumulative_gate_v0 import sha,PE_SHA,BV_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
PY
printf '[8/8] Publish report once and show SHA-256\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/first.json" "$OUT"
sha256sum -- "$OUT"
echo 'T7JKL/MNO/PQR CUMULATIVE SEMANTIC CUSTODY & RESEARCH P-INTENT PASS; STRUCTURAL NATIVE BV ONLY; HOST FORGEABLE; NO NATIVE LEARNING'
