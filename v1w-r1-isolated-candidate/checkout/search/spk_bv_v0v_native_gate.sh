#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
if [[ $# -ne 2 || "$1" != /tmp/* || "$2" != /tmp/* ]]; then
  echo 'usage: bash search/spk_bv_v0v_native_gate.sh /tmp/new-prefix /tmp/existing-v0u-native-13.json' >&2
  exit 2
fi
prefix="$1"; reference="$2"
for file in "${prefix}-13.json" "${prefix}-811.json"; do
  if [[ -e "$file" || -L "$file" ]]; then echo "refuse overwrite: $file" >&2; exit 2; fi
done
if [[ ! -f "$reference" || -L "$reference" ]]; then echo 'missing or unsafe v0u native report' >&2; exit 2; fi
echo '[1/3] Native factorial (6 cells x 3 arms) with PYTHONHASHSEED=13'
PYTHONHASHSEED=13 python -m search.spk_bv_v0v_inflight_pressure --reference-v0u "$reference" --out "${prefix}-13.json"
echo '[2/3] Independent native replay with PYTHONHASHSEED=811'
PYTHONHASHSEED=811 python -m search.spk_bv_v0v_inflight_pressure --reference-v0u "$reference" --out "${prefix}-811.json"
echo '[3/3] Cross-process equality and source-bound fixture integrity'
python - "${prefix}-13.json" "${prefix}-811.json" <<'PY'
import json,sys
from pathlib import Path
from spk_bv_research.paired_runs_v0o import load_json
from spk_bv_research.off_on_v0t import source_pins
from spk_bv_research.inflight_pressure_v0v import SCHEMA,STATUS,GRID
x,y=[load_json(Path(p)) for p in sys.argv[1:]]
if not (x==y and x.get('schema')==SCHEMA and x.get('status')==STATUS and
        x.get('source_sha256')==source_pins(Path.cwd()) and
        x.get('v0u_reference_check',{}).get('status')=='TWO_NATIVE_V0U_CAPACITY_CELLS_REPLAYED' and
        x.get('same_fixture_before_after_every_run') is True and
        len(x.get('cells',[]))==len(GRID)):
    raise SystemExit('BV v0v cross-process replay REJECTED')
print(json.dumps({'status':'NATIVE_LINK_INFLIGHT_FACTORIAL_REPLAY_PASS',
                  'cells':len(x['cells']), 'fixture_sha256':x['original_fixture_sha256']},sort_keys=True))
PY
echo 'SPK BV v0v LINK/INFLIGHT MODEL INTERVENTION PASS (not hardware/learning)'
