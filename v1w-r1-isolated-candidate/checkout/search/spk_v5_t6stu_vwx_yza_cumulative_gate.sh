#!/usr/bin/env bash
# SPK T6STU/VWX/YZA: one gate, three cumulative owned-state/restart checks.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
OUT="${1:-$HOME/workspace/spk-evidence/spk-v5-t6stu-vwx-yza-cumulative.json}"
[[ ! -e "$OUT" && ! -L "$OUT" ]] || { echo "T6STU/VWX/YZA FAIL CLOSED: REPORT_EXISTS $OUT" >&2; exit 3; }
TMP=$(mktemp -d /tmp/spk-t6stu-vwx-yza-XXXXXXXX)
trap 'rm -rf -- "$TMP"' EXIT
printf '[1/7] Verify ten cumulative manifests, frozen PE/BV and 12 original source pins\n'
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
import json,hashlib
from research.spk_v5_t6stu_vwx_yza.cumulative_gate_v0 import ANCESTRY_SHA,PE_SHA,BV_SHA
from research.spk_v5_t5mno import t5mno
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name in ('t4zabc','t5abc','t5def','t5ghi','t5jkl','t5mno','t5pqr_stu_vwx','t6abc_def_ghi','t6jkl_mno_pqr','t6stu_vwx_yza'):
    p=Path(f'research/spk_v5_{name}/manifest.json')
    assert p.is_file() and not p.is_symlink(), 'MANIFEST_MISSING_'+name
    m=json.loads(p.read_bytes())
    assert m.get('promotion_allowed') is not True and m.get('frozen_components_modified') is not True
    if name=='t6stu_vwx_yza':
        assert m['native_learning'] is False and m['native_BV_credit']==0 and m['promotion_allowed'] is False
    for path,expected in m['files'].items():
        f=Path(path)
        assert f.is_file() and not f.is_symlink() and sha(f)==expected,'SOURCE_DRIFT_'+path
    print('  ',name,len(m['files']),'SHA-pinned files')
assert sha('research/spk_v5_t6stu_vwx_yza/reference/t6jkl-mno-pqr-cumulative.json')==ANCESTRY_SHA
assert sha('spk_architecture_v1/pe_execution_v1b.py')==PE_SHA
assert sha('spk_backvalidation_v0/live_dual_scheduler_v0e.py')==BV_SHA
assert t5mno.t5jkl.custody('.',True)['original_source_pins']==12
print('  12 original source pins + frozen PE/BV verified')
PY
printf '[2/7] Twenty-seven new owned-state, crash, parity and adversarial tests\n'
PYTHONPATH=. python3 -W ignore::ResourceWarning -m unittest discover -s research/spk_v5_t6stu_vwx_yza/tests -q
printf '[3/7] Full previous research regressions\n'
for name in t6jkl_mno_pqr t6abc_def_ghi t5pqr_stu_vwx t5mno t5jkl t5ghi t5def t5abc t4zabc; do
    PYTHONPATH=. python3 -m unittest discover -s "research/spk_v5_${name}/tests" -q
done
printf '[4/7] Ancestral T6 verification and first strict research execution\n'
PYTHONPATH=. python3 -m research.spk_v5_t6stu_vwx_yza.cumulative_gate_v0 --root . --out "$TMP/one.json"
printf '[5/7] Second strict research execution in an independent Python process\n'
PYTHONPATH=. python3 -m research.spk_v5_t6stu_vwx_yza.cumulative_gate_v0 --root . --out "$TMP/two.json"
cmp -- "$TMP/one.json" "$TMP/two.json"
printf '[6/7] Fail-closed model-only attribution, transaction and replay assertions\n'
python3 - "$TMP/one.json" <<'PY'
import sys,json
r=json.load(open(sys.argv[1],encoding='utf8'))
a,b,c=r['T6STU'],r['T6VWX'],r['T6YZA']
assert a['owner']=='C' and a['domain']=='P' and a['state_update_writes_versioned_P']
assert not a['native_SPK_memory_contract_bound'] and not a['frozen_BV_scheduler_used']
assert b['scenarios']==8 and b['scenarios_reopened_each_batch']==8 and b['recovered_parity_byte_exact']
assert [p['joint_successes'] for p in b['case_results']]==[80,48,80,80,80,40,48,44]
assert b['ten_restarted_jitter_seeds_successes']==[80]*10
assert b['model_adaptive_updates']==8 and b['model_control_successes']==48 and b['model_adaptive_successes']==80
assert c['durable_vote_and_commit_recovered'] and c['one_commit_after_reopen'] and c['duplicate_rejected_after_reopen']
assert c['stale_pending_vote_rejected'] and c['privileged_host_impersonation_succeeds']
assert c['privileged_DB_mutation_detected_without_reseal']
assert r['host_can_forge'] and r['host_can_replace_full_SQLite_ledger'] and r['native_learning'] is False
assert r['native_C_policy_modified'] is False and r['native_BV_credit']==0 and r['promotion_allowed'] is False
assert r['original_source_pins']==12 and b['source_T6_jkl_replay_byte_exact']
print('  C-owned research P-state, transactional commit, restart parity and explicit host forgery PASS')
PY
printf '[7/7] Seal report without overwriting existing evidence\n'
mkdir -p -- "$(dirname -- "$OUT")"
cp -- "$TMP/one.json" "$OUT"
sha256sum -- "$OUT"
echo 'T6STU/VWX/YZA CUMULATIVE PERSISTENT C-OWNED RESEARCH STATE PASS; FULL PE FRAGMENT PARITY; HOST FORGEABLE; NO NATIVE BV OR LEARNING'
