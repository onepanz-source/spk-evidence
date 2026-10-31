#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
if [[ $# -ne 1 ]]; then echo 'usage: bash search/spk_bv_v0o_native_gate.sh /tmp/new-prefix' >&2; exit 2; fi
PREFIX="$1"
if [[ "$PREFIX" != /tmp/* ]]; then echo 'native gate requires /tmp/ prefix' >&2; exit 2; fi
for p in "${PREFIX}-13.json" "${PREFIX}-811.json" "${PREFIX}-inventory.json"; do
  if [[ -e "$p" || -L "$p" ]]; then echo "refuse overwrite: $p" >&2;exit 2;fi
done
echo '[1/4] Native v0e live scheduler source-bound fixture capture, process 13'
PYTHONHASHSEED=13 python -m search.spk_bv_v0o_capture --out "${PREFIX}-13.json"
echo '[2/4] Native v0e live scheduler source-bound fixture capture, process 811'
PYTHONHASHSEED=811 python -m search.spk_bv_v0o_capture --out "${PREFIX}-811.json"
echo '[3/4] Cross-process captured payload & source equality'
SHA=$(python - "${PREFIX}-13.json" "${PREFIX}-811.json" <<'PY'
import json,sys
from spk_bv_research.paired_runs_v0o import load_capture
x=load_capture(__import__('pathlib').Path(sys.argv[1]));y=load_capture(__import__('pathlib').Path(sys.argv[2]))
if x['native_fixture_sha256']!=y['native_fixture_sha256'] or x['producer_pins']!=y['producer_pins']:
    raise SystemExit('NATIVE RUN FIXTURE DRIFT: hashseed-invariant witness FAIL')
print(x['native_fixture_sha256'])
PY
)
echo "NATIVE_RUN_FIXTURE_SHA256=$SHA"
echo '[4/4] Emit structural inventory without guessing ON/OFF pairing'
python -m search.spk_bv_v0o_analyze --capture "${PREFIX}-13.json" --expected-fixture-sha "$SHA" --out "${PREFIX}-inventory.json"
echo "INVENTORY_FILE=${PREFIX}-inventory.json"
echo 'SPK BV v0o NATIVE SOURCE PAIR DISCOVERY PASS (not controlled causal A/B)'
