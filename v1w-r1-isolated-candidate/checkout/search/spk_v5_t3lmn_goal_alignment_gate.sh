#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
UCI="${1:?Specify original UCI data directory}"
OUT="${2:-/tmp/spk-v5-t3lmn-goal-alignment.json}"
export SPK_T3IJK_UCI_DIR="$UCI"
echo '[1/7] Inherited T3a-T3h custody and T3i/j/k pins'
python - <<'PY'
from search.spk_v5_t3ijk_closed_loop import pins_ok as i
from search.spk_v5_t3a_external_uci import pins_ok as a
from search.spk_v5_t3b_authentic_uci import check_new_pins as b
from search.spk_v5_t3c_public_full_coverage import new_pins_ok as c
from search.spk_v5_t3d_real_transition import t3d_pins_ok as d
from search.spk_v5_t3e_successor_competition import t3e_pins_ok as e
from search.spk_v5_t3f_day_stratification import t3f_pins_ok as f
from search.spk_v5_t3g_prospective import pins_ok as g
from search.spk_v5_t3h_c_owned_credit import pins_ok as h
a();b();c();d();e();f();g();h();i()
print('Inherited source SHA custody PASS')
PY
echo '[2/7] Bundled T3l/m/n SHA custody'
python - <<'PY'
from search.spk_v5_t3lmn_goal_alignment import pins_ok
print('T3l/m/n pinned SHA count:',pins_ok())
PY
echo '[3/7] New paired-world, public-goal, no-promotion tests'
python -m unittest tests.test_spk_v5_t3l_goal_identifiability tests.test_spk_v5_t3m_goal_audit tests.test_spk_v5_t3n_nonpromotion -q
echo '[4/7] Inherited T3i/j/k - T3a regression'
python -m unittest tests.test_spk_v5_t3i_online_credit tests.test_spk_v5_t3j_regime_replay tests.test_spk_v5_t3k_closed_loop_audit -q
python -m unittest tests.test_spk_v5_t3h_c_owned_credit tests.test_spk_v5_t3g_prospective tests.test_spk_v5_t3f_day_stratification -q
python -m unittest tests.test_spk_v5_t3e_successor_competition tests.test_spk_v5_t3d_real_transition -q
python -m unittest tests.test_spk_v5_t3c_public_audit tests.test_spk_v5_t3b_authentic_uci tests.test_spk_v5_t3a_external_uci -q
echo '[5/7] Frozen A1b/BV v0e'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_spk_arch_a1b_pe_execution_v1b.py tests/test_spk_bv_live_dual_scheduler_v0e.py
echo '[6/7] Original UCI: source-authentic posthoc goal and paired constructed worlds'
python search/spk_v5_t3lmn_goal_alignment.py --uci-dir "$UCI" --out "$OUT"
python - "$OUT" <<'PY'
import hashlib,sys
from pathlib import Path
actual=Path(sys.argv[1]).read_bytes()
reference=Path('docs/spk-v5-t3lmn-reference.json').read_bytes()
assert actual==reference,'T3l/m/n canonical exact replay mismatch'
print('T3LMN ORIGINAL UCI REPLAY BYTE-EXACT PASS')
print('reference_report_sha256',hashlib.sha256(reference).hexdigest())
PY
echo '[7/7] No native learning/no blind/no authenticated C sensor boundary'
python - <<'PY'
import json
from pathlib import Path
m=json.loads(Path('docs/spk-v5-t3lmn-manifest.json').read_text())
assert m['frozen_contracts_untouched'] and m['native_learning_none']
assert m['blind_claim_none'] and m['goal_label_never_in_policy']
print('T3LMN GOAL-NONIDENTIFIABILITY & PROXY MISALIGNMENT PASS; NO BLIND, NATIVE BV OR NATIVE RL')
PY
