#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
printf '[1/7] Frozen T3a, T3b, T3c original source custody\n'
python - <<'PY'
from search.spk_v5_t3a_external_uci import pins_ok
from search.spk_v5_t3b_authentic_uci import check_new_pins
from search.spk_v5_t3c_public_full_coverage import new_pins_ok
pins_ok();check_new_pins();new_pins_ok()
print('T3a/T3b/T3c pins PASS')
PY
printf '[2/7] V5-T3d new source custody\n'
python - <<'PY'
from search.spk_v5_t3d_real_transition import t3d_pins_ok
t3d_pins_ok();print('T3d pins PASS')
PY
printf '[3/7] Real-successor, physical timestamp, A1b semantic and label nonleakage tests\n'
python -m unittest tests.test_spk_v5_t3d_real_transition -q
printf '[4/7] Inherited T3c real-UCI falsification regressions\n'
python -m unittest tests.test_spk_v5_t3c_public_audit -q
printf '[5/7] Inherited T3b+T3a ingress and anti-label-leakage regressions\n'
python -m unittest tests.test_spk_v5_t3b_authentic_uci tests.test_spk_v5_t3a_external_uci -q
printf '[6/7] Frozen BV v0e and PE Architecture A1b conformance\n'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_spk_arch_a1b_pe_execution_v1b.py tests/test_spk_bv_live_dual_scheduler_v0e.py
printf '[7/7] Raw original UCI source-engine replay (optional positional source dir and T3c report)\n'
if [[ $# -eq 0 ]]; then
  printf 'EXTERNAL ORIGINAL UCI NOT RUN; pass directory and T3c report for byte-exact public evidence\n'
elif [[ $# -eq 2 ]]; then
  DIR="$1"
  REPORT="$2"
  TEMP="$(mktemp -d -t spk-v5-t3d-replay-XXXXXXXX)"
  trap 'rm -rf "$TEMP"' EXIT
  python search/spk_v5_t3d_real_transition.py \
    --train "$DIR/datatraining.txt" \
    --early "$DIR/datatest.txt" \
    --late "$DIR/datatest2.txt" \
    --t3c-report "$REPORT" \
    --t3c-sha256 388147a99e6407157b3ca3f4650d11b2cb169d25d292bbc25bcd1296ff7b0d01 \
    --out "$TEMP/report.json"
  cmp "$TEMP/report.json" docs/spk-v5-t3d-original-uci-reference.json
  printf 'T3d original-UCI canonical replay BYTE-EXACT PASS\n'
else
  printf 'Usage: bash %s [~/Scaricati/occupancy /tmp/spk-v5-t3c-original-uci-full-coverage.json]\n' "$0" >&2
  exit 2
fi
printf 'T3D REAL-PHYSICAL-SUCCESSOR INPUT PASS; OCCUPANCY ONSET UTILITY NOT PROVEN; T3 BLIND AND NATIVE RL BLOCKED\n'
