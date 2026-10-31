#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
REPORT="${1:?usage: bash search/spk_v5_t3a_external_uci_gate.sh /tmp/NEW-selftest.json}"
echo '[1/6] V5-T3a SHA custody: frozen core/architecture and previous stages'
python - <<'PY'
from pathlib import Path
import json,hashlib
m=json.loads(Path('docs/spk-v5-t3a-manifest.json').read_text())
for name,expected in m['pins_sha256'].items():
    f=Path(name)
    if not f.is_file() or f.is_symlink() or hashlib.sha256(f.read_bytes()).hexdigest()!=expected:
        raise SystemExit('V5-T3a source SHA drift: '+name)
print('source pins PASS:',len(m['pins_sha256']))
PY
echo '[2/6] V5-T3a public UCI adapter, anti-leakage and forged-custody adversarial tests'
python -m unittest tests.test_spk_v5_t3a_external_uci -q
echo '[3/6] T2h derived shared-tick arbitration and T2g residual service regressions'
python -m unittest tests.test_spk_v5_t2h_interleaved_scheduler tests.test_spk_v5_t2g_residual_service -q
echo '[4/6] A1b PE and BV v0e frozen conformance regressions'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_spk_arch_a1b_pe_execution_v1b.py tests/test_spk_bv_live_dual_scheduler_v0e.py
echo '[5/6] A1b-backed engineered selftest report (no original UCI rows)'
python search/spk_v5_t3a_external_uci.py selftest --out "$REPORT"
echo '[6/6] Exact canonical engineered reference; no misleading scientific claims'
python - "$REPORT" <<'PY'
import json,hashlib,sys
from pathlib import Path
actual=Path(sys.argv[1]).read_bytes()
expected=Path('docs/spk-v5-t3a-selftest-reference.json').read_bytes()
if actual!=expected:raise SystemExit('selftest report mismatch')
data=json.loads(actual)
assert data['phase']=='evaluation'
assert data['status']=='ENGINEERED_SELFTEST_ONLY_NOT_PUBLIC_DATA'
assert data['selftest_no_external_data_executed'] and data['selftest_labels_engineered']
assert not data['blind_holdout_claim'] and not data['endogenous_BV_reward_established']
assert data['native_program_updates']==0
print('report_sha256',hashlib.sha256(actual).hexdigest())
print('T3A PUBLIC-DATA ADAPTER / LEAKAGE GATES PASS; ACTUAL UCI DATA NOT RUN; BLIND RL & NATIVE LEARNING BLOCKED')
PY
