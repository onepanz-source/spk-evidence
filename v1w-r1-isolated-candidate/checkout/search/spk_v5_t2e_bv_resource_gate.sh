#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUTPUT="${1:?usage: bash search/spk_v5_t2e_bv_resource_gate.sh /tmp/new-report.json}"
printf '[1/8] T2e immutable-source custody and reference\n'
python - <<'PY'
import hashlib,json,pathlib
manifest=json.loads(pathlib.Path('docs/spk-v5-t2e-manifest.json').read_text())
for rel,sha in manifest['pins_sha256'].items():
    p=pathlib.Path(rel)
    if not p.is_file() or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
        raise SystemExit('V5-T2e source pin drift: '+rel)
print('source pins PASS:',len(manifest['pins_sha256']))
PY
printf '[2/8] V5-T2e source replay, resource conservation and adversarial tests\n'
python -m unittest tests.test_spk_v5_t2e_bv_resource_bridge -q
printf '[3/8] V5-T2d inherited sensor robustness\n'
python -m unittest tests.test_spk_v5_t2d_sensor_robustness -q
printf '[4/8] V5-T2c inherited closed bandit\n'
python -m unittest tests.test_spk_v5_t2c_exogenous_demand -q
printf '[5/8] Inherited T2b and T1/T2 island objective\n'
python -m unittest tests.test_spk_v5_t2b_local_consequence tests.test_spk_v5_t1_island_objective -q
printf '[6/8] Frozen BV v0e and Architecture A1b conformances\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_spk_bv_live_dual_scheduler_v0e.py tests/test_spk_arch_a1b_pe_execution_v1b.py -q
printf '[7/8] Source-executed create-only evidence report\n'
python search/spk_v5_t2e_bv_resource_bridge.py "$OUTPUT"
printf '[8/8] Canonical byte-exact reference and bounded research decision\n'
python - "$OUTPUT" <<'PY'
from pathlib import Path
import hashlib,sys
reference=Path('docs/spk-v5-t2e-reference.json').read_bytes()
actual=Path(sys.argv[1]).read_bytes()
if actual!=reference:raise SystemExit('V5-T2e noncanonical / source mismatch')
print('report_sha256',hashlib.sha256(actual).hexdigest())
print('T2E ABSTRACT BV COSTS CHARGED; SILENT SEMANTIC REWARD CANNOT ROUTE; T3 BLIND BLOCKED; NATIVE LEARNING NONE')
PY
