#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
printf '[1/6] Frozen T3a source+frozen architecture custody (49 pins)\n'
python - <<'PY'
from search.spk_v5_t3a_external_uci import pins_ok
pins_ok()
print('frozen T3a pins PASS')
PY
printf '[2/6] Previous T3b hotfix source custody (6 pins)\n'
python - <<'PY'
from search.spk_v5_t3b_authentic_uci import check_new_pins
check_new_pins()
print('T3b pins PASS')
PY
printf '[3/6] T3c additive source pins\n'
python - <<'PY'
from search.spk_v5_t3c_public_full_coverage import new_pins_ok
new_pins_ok()
print('T3c pins PASS')
PY
printf '[4/6] T3c external source, full A1b replay, disjoint cohorts, static equivalence, adversarial custody\n'
python -m unittest tests.test_spk_v5_t3c_public_audit -q
printf '[5/6] Inherited T3b and T3a data anti-leakage regressions\n'
python -m unittest tests.test_spk_v5_t3b_authentic_uci tests.test_spk_v5_t3a_external_uci -q
printf '[6/6] Inherited frozen Architecture A1b and BV scheduler v0e conformance\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_spk_arch_a1b_pe_execution_v1b.py tests/test_spk_bv_live_dual_scheduler_v0e.py
printf 'T3C PUBLIC AUDITOR GATE PASS; RAW UCI RUN SEPARATE; TEMPORAL PHYSICS AND NATIVE RL NOT DEMONSTRATED\n'
