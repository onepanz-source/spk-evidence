#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo '[1/9] Frozen T3a-T3f source custody'
python - <<'PY'
from search.spk_v5_t3a_external_uci import pins_ok
from search.spk_v5_t3b_authentic_uci import check_new_pins
from search.spk_v5_t3c_public_full_coverage import new_pins_ok
from search.spk_v5_t3d_real_transition import t3d_pins_ok
from search.spk_v5_t3e_successor_competition import t3e_pins_ok
from search.spk_v5_t3f_day_stratification import t3f_pins_ok
pins_ok();check_new_pins();new_pins_ok();t3d_pins_ok();t3e_pins_ok();t3f_pins_ok()
print('T3a-T3f source SHA custody PASS')
PY
echo '[2/9] T3g new source SHA custody'
python - <<'PY'
from search.spk_v5_t3g_prospective import pins_ok
pins_ok();print('T3g source SHA custody PASS')
PY
echo '[3/9] Prospective no-label precommit, source integrity and adversarial tests'
python -m unittest tests.test_spk_v5_t3g_prospective -q
echo '[4/9] Inherited T3f public posthoc audit regression'
python -m unittest tests.test_spk_v5_t3f_day_stratification -q
echo '[5/9] Inherited T3e physical-successor competitor regression'
python -m unittest tests.test_spk_v5_t3e_successor_competition -q
echo '[6/9] Inherited T3d and T3c research regressions'
python -m unittest tests.test_spk_v5_t3d_real_transition tests.test_spk_v5_t3c_public_audit -q
echo '[7/9] Inherited T3b/T3a no-label leakage regressions'
python -m unittest tests.test_spk_v5_t3b_authentic_uci tests.test_spk_v5_t3a_external_uci -q
echo '[8/9] Frozen A1b and BV v0e'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_spk_arch_a1b_pe_execution_v1b.py tests/test_spk_bv_live_dual_scheduler_v0e.py
echo '[9/9] Prospectivity gate (no UCI report, no hidden/novel real data)'
python - <<'PY'
import json
from pathlib import Path
from spk_v5_research.island_prospective_validation_v5t3g import SCHEMA
m=json.loads(Path('docs/spk-v5-t3g-manifest.json').read_text())
assert m['no_unseen_external_data_claim'] and m['native_learning_none'] and m['new_schema']==SCHEMA
print('T3G PRE-REGISTERED PROSPECTIVE SCREEN CONTRACT PASS; NO FRESH DATA TESTED; NO BLIND ESCROW OR NATIVE RL')
PY
