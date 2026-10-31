#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUTPUT="${1:?usage: bash search/spk_v5_t2d_sensor_robustness_gate.sh /tmp/new-report.json}"
printf '[1/7] V5-T2d all source SHA custody and frozen contracts\n'
python - <<'PY'
import hashlib,json,pathlib
m=json.loads(pathlib.Path('docs/spk-v5-t2d-manifest.json').read_text())
for rel,expected in m['pins_sha256'].items():
    p=pathlib.Path(rel)
    if not p.is_file() or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
        raise SystemExit('V5-T2d source custody FAIL: '+rel)
print('source pins PASS:',len(m['pins_sha256']))
PY
printf '[2/7] V5-T2d local sensor faults, blind-to-learner and adversarial audit\n'
python -m unittest tests.test_spk_v5_t2d_sensor_robustness -q
printf '[3/7] Inherited V5-T2c exogenous demand research tests\n'
python -m unittest tests.test_spk_v5_t2c_exogenous_demand -q
printf '[4/7] Inherited V5-T2b and V5-T1/T2 tests\n'
python -m unittest tests.test_spk_v5_t2b_local_consequence tests.test_spk_v5_t1_island_objective -q
printf '[5/7] Frozen Architecture A1b PE conformity tests\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_spk_arch_a1b_pe_execution_v1b.py -q
printf '[6/7] Source-engine create-only V5-T2d canonical report\n'
python search/spk_v5_t2d_sensor_robustness.py "$OUTPUT"
printf '[7/7] Byte-exact reference / research boundary\n'
python - "$OUTPUT" <<'PY'
import hashlib,pathlib,sys
reference=pathlib.Path('docs/spk-v5-t2d-reference.json').read_bytes()
actual=pathlib.Path(sys.argv[1]).read_bytes()
if actual!=reference:
    raise SystemExit('V5-T2d reference mismatch')
print('report_sha256',hashlib.sha256(actual).hexdigest())
print('T2D SENSOR FAILURE MODES VERIFIED; NO INDEPENDENT TRUTH, NO NATIVE REVERSE BV OR LEARNING; T3 BLIND BLOCKED')
PY
