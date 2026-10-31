#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
UCI="${1:?Specify directory containing authentic datatraining.txt, datatest.txt, datatest2.txt}"
OUT="${2:-/tmp/spk-v5-t3ijk-closed-loop-research.json}"
export SPK_T3IJK_UCI_DIR="$UCI"
echo '[1/8] Frozen T3a-T3h source SHA pins'
python - <<'PY'
from search.spk_v5_t3a_external_uci import pins_ok as a
from search.spk_v5_t3b_authentic_uci import check_new_pins as b
from search.spk_v5_t3c_public_full_coverage import new_pins_ok as c
from search.spk_v5_t3d_real_transition import t3d_pins_ok as d
from search.spk_v5_t3e_successor_competition import t3e_pins_ok as e
from search.spk_v5_t3f_day_stratification import t3f_pins_ok as f
from search.spk_v5_t3g_prospective import pins_ok as g
from search.spk_v5_t3h_c_owned_credit import pins_ok as h
a();b();c();d();e();f();g();h();print('Inherited T3a-T3h SHA pins PASS')
PY
echo '[2/8] Bundled T3i/j/k pin custody'
python - <<'PY'
from search.spk_v5_t3ijk_closed_loop import pins_ok
print(pins_ok(),'bundled pinned sources PASS')
PY
echo '[3/8] New T3i/j/k online custody, engineered regimes, public bounds'
python -m unittest tests.test_spk_v5_t3i_online_credit tests.test_spk_v5_t3j_regime_replay tests.test_spk_v5_t3k_closed_loop_audit -q
echo '[4/8] Inherited T3h/T3g/T3f regression'
python -m unittest tests.test_spk_v5_t3h_c_owned_credit tests.test_spk_v5_t3g_prospective tests.test_spk_v5_t3f_day_stratification -q
echo '[5/8] Inherited T3e/T3d/T3c/T3b/T3a regression'
python -m unittest tests.test_spk_v5_t3e_successor_competition tests.test_spk_v5_t3d_real_transition -q
python -m unittest tests.test_spk_v5_t3c_public_audit tests.test_spk_v5_t3b_authentic_uci tests.test_spk_v5_t3a_external_uci -q
echo '[6/8] Frozen A1b and BV v0e'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_spk_arch_a1b_pe_execution_v1b.py tests/test_spk_bv_live_dual_scheduler_v0e.py
echo '[7/8] Original UCI + source-gated create-only report'
python search/spk_v5_t3ijk_closed_loop.py --uci-dir "$UCI" --out "$OUT"
python - "$OUT" <<'PY'
from pathlib import Path
import hashlib,sys
report=Path(sys.argv[1]).read_bytes()
reference=Path('docs/spk-v5-t3ijk-reference.json').read_bytes()
assert report==reference,'T3i/j/k canonical full research report drift'
print('T3IJK FULL CANONICAL REPLAY BYTE-EXACT PASS')
print('reference_report_sha256',hashlib.sha256(reference).hexdigest())
PY
echo '[8/8] Research boundary'
python - <<'PY'
from pathlib import Path
import json
m=json.loads(Path('docs/spk-v5-t3ijk-manifest.json').read_text())
assert m['frozen_contracts_untouched'] and m['native_learning_none']
assert m['photo_label_never_used_for_update'] and m['research_host_controller_not_neuron_A']
assert len(m['new_files'])==11 and len(m['pins_sha256'])>=10
print('T3IJK C-AUTHORED RESEARCH CLOSED LOOP PASS; ENGINEERED SHIFT ONLY, UCI PROXY MISALIGNMENT, NO BLIND OR NATIVE RL')
PY
