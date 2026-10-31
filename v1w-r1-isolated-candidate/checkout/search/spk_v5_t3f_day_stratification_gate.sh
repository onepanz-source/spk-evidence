#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo '[1/8] Inherited T3a-T3e frozen source SHA custody'
python - <<'PY'
from search.spk_v5_t3a_external_uci import pins_ok
from search.spk_v5_t3b_authentic_uci import check_new_pins
from search.spk_v5_t3c_public_full_coverage import new_pins_ok
from search.spk_v5_t3d_real_transition import t3d_pins_ok
from search.spk_v5_t3e_successor_competition import t3e_pins_ok
pins_ok();check_new_pins();new_pins_ok();t3d_pins_ok();t3e_pins_ok()
print('Inherited T3 source custody PASS')
PY
echo '[2/8] New T3f SHA custody'
python - <<'PY'
from search.spk_v5_t3f_day_stratification import t3f_pins_ok
t3f_pins_ok();print('T3f source SHA custody PASS')
PY
echo '[3/8] New day-block no-label-leakage and falsification tests'
python -m unittest tests.test_spk_v5_t3f_day_stratification -q
echo '[4/8] T3e source-A1b temporal-vs-current regressions'
python -m unittest tests.test_spk_v5_t3e_successor_competition -q
echo '[5/8] T3d physical-successor & T3c static equivalence regressions'
python -m unittest tests.test_spk_v5_t3d_real_transition tests.test_spk_v5_t3c_public_audit -q
echo '[6/8] T3b/T3a original-input strict source & label isolation regressions'
python -m unittest tests.test_spk_v5_t3b_authentic_uci tests.test_spk_v5_t3a_external_uci -q
echo '[7/8] Frozen A1b + BV v0e'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_spk_arch_a1b_pe_execution_v1b.py tests/test_spk_bv_live_dual_scheduler_v0e.py
echo '[8/8] Source-grounded original UCI report (if originals supplied)'
if [[ $# -eq 0 ]]; then
  echo 'No original UCI provided: functional tests PASS, original UCI replay NOT RUN'
elif [[ $# -eq 1 ]]; then
  DIR="$1"
  TMP="$(mktemp -d -t spk-v5-t3f-XXXXXX)"
  trap 'rm -rf "$TMP"' EXIT
  python search/spk_v5_t3f_day_stratification.py \
    --train "$DIR/datatraining.txt" --early "$DIR/datatest.txt" --late "$DIR/datatest2.txt" \
    --t3e-report docs/spk-v5-t3e-original-uci-reference.json \
    --t3e-sha256 b6e4ca2752fdd9df6be7e0247b4c8474dbe5a6f4e7dca1c169ecac10430a4833 \
    --out "$TMP/t3f.json"
  cmp "$TMP/t3f.json" docs/spk-v5-t3f-original-uci-reference.json
  echo 'T3F ORIGINAL UCI CANONICAL REPLAY BYTE-EXACT PASS'
else
  echo "Usage: bash $0 [original-UCI-directory]" >&2
  exit 2
fi
echo 'T3F PUBLIC DAY-STRATIFIED FALSIFICATION PASS; NOT BLIND; NATIVE LEARNING NONE'
