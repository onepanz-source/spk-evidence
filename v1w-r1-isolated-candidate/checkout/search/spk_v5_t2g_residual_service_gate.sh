#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUTPUT="${1:?usage: bash search/spk_v5_t2g_residual_service_gate.sh /tmp/new-report.json}"
printf '[1/10] V5-T2g 37 source SHA pins including frozen native and inherited V5\n'
python - <<'PY'
import json,hashlib,pathlib
m=json.loads(pathlib.Path('docs/spk-v5-t2g-manifest.json').read_text())
for rel,pin in m['pins_sha256'].items():
    p=pathlib.Path(rel)
    if not p.is_file() or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=pin:
        raise SystemExit('T2g pin failure: '+rel)
print('source pins PASS:',len(m['pins_sha256']))
PY
printf '[2/10] V5-T2g source-grounded residual capacity and adversarial tests\n'
python -m unittest tests.test_spk_v5_t2g_residual_service -q
printf '[3/10] Inherited V5-T2f decision/reward custody tests\n'
python -m unittest tests.test_spk_v5_t2f_island_decision_reward -q
printf '[4/10] Inherited V5-T2e source BV v0e accounting tests\n'
python -m unittest tests.test_spk_v5_t2e_bv_resource_bridge -q
printf '[5/10] Inherited V5-T2d sensor fault tests\n'
python -m unittest tests.test_spk_v5_t2d_sensor_robustness -q
printf '[6/10] Inherited V5-T2c bandit tests\n'
python -m unittest tests.test_spk_v5_t2c_exogenous_demand -q
printf '[7/10] Inherited V5-T2b and T1/T2 tests\n'
python -m unittest tests.test_spk_v5_t2b_local_consequence tests.test_spk_v5_t1_island_objective -q
printf '[8/10] Original BV v0e and frozen A1b tests\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_spk_bv_live_dual_scheduler_v0e.py tests/test_spk_arch_a1b_pe_execution_v1b.py -q
printf '[9/10] Original BV v0e + A1b source-replayed create-only T2g report\n'
python search/spk_v5_t2g_residual_service.py "$OUTPUT"
printf '[10/10] Byte exact reference, research boundary and report digest\n'
python - "$OUTPUT" <<'PY'
import hashlib,json,sys
from pathlib import Path
actual=Path(sys.argv[1]).read_bytes()
ref=Path('docs/spk-v5-t2g-reference.json').read_bytes()
if actual!=ref:raise SystemExit('T2g report mismatch: not releasable')
report=json.loads(actual)
assert report['shadow_grants_native'] is False and report['native_learner_updates']==0
print('report_sha256',hashlib.sha256(actual).hexdigest())
print('T2G SOURCE-GROUNDED SHADOW RESIDUAL SERVICE PASS; NATIVE INTEGRATION AND T3 BLIND BLOCKED; NATIVE LEARNING NONE')
PY
