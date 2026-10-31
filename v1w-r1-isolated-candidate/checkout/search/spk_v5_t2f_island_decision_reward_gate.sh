#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUTPUT="${1:?usage: bash search/spk_v5_t2f_island_decision_reward_gate.sh /tmp/new-report.json}"
printf '[1/9] V5-T2f pinned source, frozen native, prior V5 custody\n'
python - <<'PY'
import hashlib,json,pathlib
manifest=json.loads(pathlib.Path('docs/spk-v5-t2f-manifest.json').read_text())
for rel,sha in manifest['pins_sha256'].items():
    p=pathlib.Path(rel)
    if not p.is_file() or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
        raise SystemExit('T2f source SHA mismatch: '+rel)
print('source pins PASS:',len(manifest['pins_sha256']))
PY
printf '[2/9] T2f shadow decision, silence credit, paid-route adversarial tests\n'
python -m unittest tests.test_spk_v5_t2f_island_decision_reward -q
printf '[3/9] Inherited T2e abstract BV resource bridge tests\n'
python -m unittest tests.test_spk_v5_t2e_bv_resource_bridge -q
printf '[4/9] Inherited T2d sensor fault tests\n'
python -m unittest tests.test_spk_v5_t2d_sensor_robustness -q
printf '[5/9] Inherited T2c single-arm bandit research tests\n'
python -m unittest tests.test_spk_v5_t2c_exogenous_demand -q
printf '[6/9] Inherited T2b and T1/T2 source objective tests\n'
python -m unittest tests.test_spk_v5_t2b_local_consequence tests.test_spk_v5_t1_island_objective -q
printf '[7/9] Frozen BV v0e and Architecture A1b regressions\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_spk_bv_live_dual_scheduler_v0e.py tests/test_spk_arch_a1b_pe_execution_v1b.py -q
printf '[8/9] Source engine create-only observational report\n'
python search/spk_v5_t2f_island_decision_reward.py "$OUTPUT"
printf '[9/9] Byte-exact reference and bounded research verdict\n'
python - "$OUTPUT" <<'PY'
from pathlib import Path
import hashlib,sys
actual=Path(sys.argv[1]).read_bytes()
reference=Path('docs/spk-v5-t2f-reference.json').read_bytes()
if actual != reference:
    raise SystemExit('V5-T2f noncanonical report, refusing research closure')
print('report_sha256',hashlib.sha256(actual).hexdigest())
print('T2F PAID SHADOW DECISION/REWARD PROTOCOL PASS; NATIVE ROUTE, INDEPENDENT TRUTH AND T3 BLIND BLOCKED; NATIVE LEARNING NONE')
PY
