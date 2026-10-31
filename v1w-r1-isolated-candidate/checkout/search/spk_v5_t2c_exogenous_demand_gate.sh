#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUTPUT="${1:?usage: bash search/spk_v5_t2c_exogenous_demand_gate.sh /tmp/new-report.json}"
printf '[1/7] V5-T2c pinned source custody and T2b predecessor\n'
python - <<'PY'
import hashlib,json,pathlib
root=pathlib.Path('.').resolve()
m=json.loads((root/'docs/spk-v5-t2c-manifest.json').read_text())
for rel,expected in m['pins_sha256'].items():
    p=root/rel
    if not p.is_file() or p.is_symlink():raise SystemExit('missing or symlinked pinned source: '+rel)
    if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise SystemExit('SHA drift: '+rel)
print('source pins PASS:',len(m['pins_sha256']))
PY
printf '[2/7] V5-T2c exogenous C-demand, closure, bandit and adversarial tests\n'
python -m unittest tests.test_spk_v5_t2c_exogenous_demand -q
printf '[3/7] Inherited V5-T2b local consequence tests\n'
python -m unittest tests.test_spk_v5_t2b_local_consequence -q
printf '[4/7] Inherited V5-T1/T2 objective boundary tests\n'
python -m unittest tests.test_spk_v5_t1_island_objective -q
printf '[5/7] Frozen A1b PE conformity regressions\n'
python -m pytest tests/test_spk_arch_a1b_pe_execution_v1b.py -q
printf '[6/7] A1b source-engine create-only V5-T2c observation\n'
python search/spk_v5_t2c_exogenous_demand.py "$OUTPUT"
printf '[7/7] Canonical byte-exact reference and research-only conclusion\n'
python - "$OUTPUT" <<'PY'
import hashlib,pathlib,sys
reference=pathlib.Path('docs/spk-v5-t2c-reference.json').read_bytes()
actual=pathlib.Path(sys.argv[1]).read_bytes()
if reference!=actual:raise SystemExit('V5-T2c byte-exact reference mismatch')
print('report_sha256',hashlib.sha256(actual).hexdigest())
print('T2C SYNTHETIC C-DEMAND BANDIT CONTROL PASS; INDEPENDENT TASK TRUTH & T3 BLIND BLOCKED; NATIVE LEARNING NONE')
PY
