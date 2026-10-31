#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo '[1/4] Frozen T3a 49 source SHA pins'
python - <<'PY'
from search.spk_v5_t3a_external_uci import pins_ok
pins_ok()
print('original T3a SHA pins PASS')
PY
echo '[2/4] Additive T3b original UCI format source SHA pins'
python - <<'PY'
from search.spk_v5_t3b_authentic_uci import check_new_pins
check_new_pins()
print('new T3b SHA pins PASS')
PY
echo '[3/4] Authentic UCI indexed format, causal input isolation and anti-leakage tests'
python -m unittest tests.test_spk_v5_t3b_authentic_uci -q
echo '[4/4] Frozen T3a anti-leakage and synthetic selftest regression'
python -m unittest tests.test_spk_v5_t3a_external_uci -q
echo 'T3B ORIGINAL UCI CSV PARSER PASS; PUBLIC EXTERNAL TEST NOT BLIND; NATIVE LEARNING NONE'
