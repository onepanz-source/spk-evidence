#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUTPUT="${1:?usage: bash search/spk_v5_t2h_integrated_gate.sh /tmp/NEW-report.json}"
printf '[1/11] T2h SHA source pins, inherited V5 and native source\n'
python - <<'PY'
import hashlib,json
from pathlib import Path
m=json.loads(Path('docs/spk-v5-t2h-manifest.json').read_text())
for rel,expected in m['pins_sha256'].items():
    p=Path(rel)
    if not p.is_file() or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
        raise SystemExit('T2h source pin mismatch: '+rel)
print('source pins PASS:',len(m['pins_sha256']))
PY
printf '[2/11] T2h integrated event-loop/shared resource/adversarial tests\n'
python -m unittest tests.test_spk_v5_t2h_interleaved_scheduler -q
printf '[3/11] Inherited T2g resource admissibility\n'
python -m unittest tests.test_spk_v5_t2g_residual_service -q
printf '[4/11] Inherited T2f decision receipt\n'
python -m unittest tests.test_spk_v5_t2f_island_decision_reward -q
printf '[5/11] Inherited T2e source BV accounting\n'
python -m unittest tests.test_spk_v5_t2e_bv_resource_bridge -q
printf '[6/11] Inherited T2d sensor adversarial suite\n'
python -m unittest tests.test_spk_v5_t2d_sensor_robustness -q
printf '[7/11] Inherited T2c bandit tests\n'
python -m unittest tests.test_spk_v5_t2c_exogenous_demand -q
printf '[8/11] Inherited T2b and T1/T2 objectives\n'
python -m unittest tests.test_spk_v5_t2b_local_consequence tests.test_spk_v5_t1_island_objective -q
printf '[9/11] Frozen BV v0e and Architecture A1b regressions\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_spk_bv_live_dual_scheduler_v0e.py tests/test_spk_arch_a1b_pe_execution_v1b.py -q
printf '[10/11] Interleaved source-engine create-only canonical report\n'
python search/spk_v5_t2h_integrated.py "$OUTPUT"
printf '[11/11] Exact canonical reference and research boundary\n'
python - "$OUTPUT" <<'PY'
from pathlib import Path
import hashlib,json,sys
actual=Path(sys.argv[1]).read_bytes()
reference=Path('docs/spk-v5-t2h-reference.json').read_bytes()
if actual!=reference:raise SystemExit('T2h report/reference disagreement')
r=json.loads(actual)
assert (not r['native_engine_modified'] and not r['native_integration'] and
        not r['blind_T3'] and r['native_learning_updates']==0)
assert r['profiles']['off']['source_forward_batch_changes_vs_off']==0
assert r['profiles']['control_first']['source_forward_batch_changes_vs_off']>=1
print('report_sha256',hashlib.sha256(actual).hexdigest())
print('T2H INTERLEAVED DERIVED ARBITRATION PASS; NATIVE INTAKE & T3 BLIND BLOCKED; NATIVE LEARNING NONE')
PY
