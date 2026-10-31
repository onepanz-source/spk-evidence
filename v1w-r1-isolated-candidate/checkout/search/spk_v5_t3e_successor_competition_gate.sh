#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
printf '[1/8] Frozen T3a-T3d source custody\n'
python - <<'PY'
from search.spk_v5_t3a_external_uci import pins_ok
from search.spk_v5_t3b_authentic_uci import check_new_pins
from search.spk_v5_t3c_public_full_coverage import new_pins_ok
from search.spk_v5_t3d_real_transition import t3d_pins_ok
pins_ok();check_new_pins();new_pins_ok();t3d_pins_ok()
print('T3a-T3d SHA custody PASS')
PY
printf '[2/8] New T3e SHA custody\n'
python - <<'PY'
from search.spk_v5_t3e_successor_competition import t3e_pins_ok
t3e_pins_ok();print('T3e SHA custody PASS')
PY
printf '[3/8] New real-successor A1b program, static comparator and adversarial controls\n'
python -m unittest tests.test_spk_v5_t3e_successor_competition -q
printf '[4/8] Inherited T3d temporal-source and anti-label-leakage tests\n'
python -m unittest tests.test_spk_v5_t3d_real_transition -q
printf '[5/8] Inherited T3c public-coverage tests\n'
python -m unittest tests.test_spk_v5_t3c_public_audit -q
printf '[6/8] Inherited T3b and T3a strict ingress tests\n'
python -m unittest tests.test_spk_v5_t3b_authentic_uci tests.test_spk_v5_t3a_external_uci -q
printf '[7/8] Frozen BV v0e and PE Architecture A1b conformance\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_spk_arch_a1b_pe_execution_v1b.py tests/test_spk_bv_live_dual_scheduler_v0e.py
printf '[8/8] Optional original UCI source + canonical predecessor replay\n'
if [[ $# -eq 0 ]]; then
  echo 'Original UCI not executed; pass original UCI directory and T3d predecessor report'
elif [[ $# -eq 2 ]]; then
  DIR="$1"; REPORT="$2"
  TMP="$(mktemp -d -t spk-v5-t3e-XXXXXX)"
  trap 'rm -rf "$TMP"' EXIT
  python search/spk_v5_t3e_successor_competition.py \
    --train "$DIR/datatraining.txt" --early "$DIR/datatest.txt" --late "$DIR/datatest2.txt" \
    --t3d-report "$REPORT" \
    --t3d-sha256 687dbc58cb3e389fd9176943ef8114951844ec936028a0b5ca0ad1e85ad86188 \
    --out "$TMP/t3e-report.json"
  cmp "$TMP/t3e-report.json" docs/spk-v5-t3e-original-uci-reference.json
  echo 'T3E ORIGINAL UCI CANONICAL REPLAY BYTE-EXACT PASS'
else
  echo "Usage: bash $0 [original-UCI-directory /tmp/T3d-report.json]" >&2
  exit 2
fi
printf 'T3E A1B PHYSICAL PERSISTENCE COMPARISON PASS; PUBLIC NOT BLIND; NATIVE LEARNING NONE\n'
