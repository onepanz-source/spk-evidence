#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo '[1/10] Inherited T3g and frozen V5 SHA source custody'
python - <<'PY'
from search.spk_v5_t3a_external_uci import pins_ok
from search.spk_v5_t3b_authentic_uci import check_new_pins
from search.spk_v5_t3c_public_full_coverage import new_pins_ok
from search.spk_v5_t3d_real_transition import t3d_pins_ok
from search.spk_v5_t3e_successor_competition import t3e_pins_ok
from search.spk_v5_t3f_day_stratification import t3f_pins_ok
from search.spk_v5_t3g_prospective import pins_ok as g_pins_ok
pins_ok();check_new_pins();new_pins_ok();t3d_pins_ok();t3e_pins_ok();t3f_pins_ok();g_pins_ok()
print('T3a-T3g  source custody PASS')
PY
echo '[2/10] New C computed A1b reward / reverse routing SHA custody'
python - <<'PY'
from search.spk_v5_t3h_c_owned_credit import pins_ok
pins_ok();print('T3h  source custody PASS')
PY
echo '[3/10] C neural computation / A consumption / missing evidence and attack regressions'
python -m unittest tests.test_spk_v5_t3h_c_owned_credit -q
echo '[4/10] Inherited T3g prospectivity and T3f public falsification regressions'
python -m unittest tests.test_spk_v5_t3g_prospective tests.test_spk_v5_t3f_day_stratification -q
echo '[5/10] Inherited T3e physical persistence and T3d physical onset regressions'
python -m unittest tests.test_spk_v5_t3e_successor_competition tests.test_spk_v5_t3d_real_transition -q
echo '[6/10] Inherited T3c public A1b, T3b UCI, T3a no leakage regressions'
python -m unittest tests.test_spk_v5_t3c_public_audit tests.test_spk_v5_t3b_authentic_uci tests.test_spk_v5_t3a_external_uci -q
echo '[7/10] Frozen Architecture A1b and BV v0e'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_spk_arch_a1b_pe_execution_v1b.py tests/test_spk_bv_live_dual_scheduler_v0e.py
echo '[8/10] Create-only source report / canonical SHA'
OUT="${1:-/tmp/spk-v5-t3h-c-owned-credit.json}"
python search/spk_v5_t3h_c_owned_credit.py --out "$OUT"
echo '[9/10] Byte-identical canonical reference'
python - "$OUT" <<'PY'
from pathlib import Path
import hashlib,sys
p=Path(sys.argv[1]);r=Path('docs/spk-v5-t3h-reference.json')
assert p.read_bytes()==r.read_bytes(),'T3h independent byte replay drift'
print('T3h independent reference BYTE-EXACT PASS')
print('reference_report_sha256',hashlib.sha256(r.read_bytes()).hexdigest())
PY
echo '[10/10] Final research boundary'
python - <<'PY'
from pathlib import Path
import json
m=json.loads(Path('docs/spk-v5-t3h-manifest.json').read_text())
assert m['native_learning_none'] and m['external_photo_labels_never_used_as_C_reward']
assert m['new_schema']=='spk-v5-t3h-c-authored-reverse-credit/research-v0'
assert len(m['new_files'])==7 and len(m['pins_sha256'])>=7
print('T3H C-COMPUTED A1B REVERSE CREDIT PASS; SENSOR AUTHORITY, NATIVE BV AND NATIVE RL BLOCKED')
PY
