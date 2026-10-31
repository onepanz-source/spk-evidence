#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="${1:-/tmp/spk-v5-t3opq-source-bv-credit.json}"
echo '[1/8] Frozen source pins from T3a through T3lmn'
python - <<'PY'
from search.spk_v5_t3ijk_closed_loop import pins_ok as i
from search.spk_v5_t3lmn_goal_alignment import pins_ok as l
from search.spk_v5_t3a_external_uci import pins_ok as a
from search.spk_v5_t3b_authentic_uci import check_new_pins as b
from search.spk_v5_t3c_public_full_coverage import new_pins_ok as c
from search.spk_v5_t3d_real_transition import t3d_pins_ok as d
from search.spk_v5_t3e_successor_competition import t3e_pins_ok as e
from search.spk_v5_t3f_day_stratification import t3f_pins_ok as f
from search.spk_v5_t3g_prospective import pins_ok as g
from search.spk_v5_t3h_c_owned_credit import pins_ok as h
a();b();c();d();e();f();g();h();i();l()
print('All inherited frozen V5 source SHA pins PASS')
PY
echo '[2/8] T3opq own SHA source pins'
python - <<'PY'
from search.spk_v5_t3opq_source_bridge import pins_ok
print('Pinned SHA count:',pins_ok())
PY
echo '[3/8] Aggregated 421 research unittest cases (60 new + 361 inherited)'
python -m unittest -q \
  tests.test_spk_v5_t3o_source_terminal_mirror tests.test_spk_v5_t3p_source_admission tests.test_spk_v5_t3q_source_bridge_audit \
  tests.test_spk_v5_t3l_goal_identifiability tests.test_spk_v5_t3m_goal_audit tests.test_spk_v5_t3n_nonpromotion \
  tests.test_spk_v5_t3i_online_credit tests.test_spk_v5_t3j_regime_replay tests.test_spk_v5_t3k_closed_loop_audit \
  tests.test_spk_v5_t3h_c_owned_credit tests.test_spk_v5_t3g_prospective tests.test_spk_v5_t3f_day_stratification \
  tests.test_spk_v5_t3e_successor_competition tests.test_spk_v5_t3d_real_transition \
  tests.test_spk_v5_t3c_public_audit tests.test_spk_v5_t3b_authentic_uci tests.test_spk_v5_t3a_external_uci
echo '[4/8] Program/source identity and causal custody covered by aggregated tests'
echo '[5/8] Native-source frozen BV regression retained separately'
echo '[6/8] 46 frozen A1b / BV v0e regressions'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_spk_arch_a1b_pe_execution_v1b.py tests/test_spk_bv_live_dual_scheduler_v0e.py
echo '[7/8] Engineered source BV replay byte-exact reference'
python search/spk_v5_t3opq_source_bridge.py --out "$OUT"
python - "$OUT" <<'PY'
import hashlib,sys
from pathlib import Path
blob=Path(sys.argv[1]).read_bytes()
ref=Path('docs/spk-v5-t3opq-reference.json').read_bytes()
assert blob==ref,'T3o/p/q source replay differs from canonical reference'
print('T3OPQ DUAL BV v0e SOURCE REPLAY BYTE-EXACT PASS')
print('reference_report_sha256',hashlib.sha256(ref).hexdigest())
PY
echo '[8/8] Research-only nonpromotion boundary'
python - <<'PY'
import json
from pathlib import Path
m=json.loads(Path('docs/spk-v5-t3opq-manifest.json').read_text())
assert m['frozen_contracts_untouched'] and m['no_native_learning']
assert m['no_authenticated_sensor'] and m['two_pass_shadow_not_native_BV_semantic_credit']
assert m['no_blind_goal_claim']
print('T3OPQ BV-v0e SOURCE CAUSAL VERDICT BRIDGE PASS; DUAL REPLAY SHADOW ONLY, NO AUTHENTICATED SENSOR, NATIVE SEMANTIC BV OR RL')
PY
