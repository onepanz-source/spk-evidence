#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
if [[ $# -ne 2 || "$1" != /tmp/* || "$2" != /tmp/* ]]; then
    echo 'usage: bash search/spk_bv_v0u_native_gate.sh /tmp/new-prefix /tmp/existing-v0t-native-13.json' >&2
    exit 2
fi
prefix="$1"; reference="$2"
for f in "${prefix}-13.json" "${prefix}-811.json"; do
    if [[ -e "$f" || -L "$f" ]]; then echo "refuse overwrite: $f" >&2; exit 2; fi
done
if [[ ! -f "$reference" || -L "$reference" ]]; then
    echo 'missing or unsafe native v0t reference' >&2; exit 2
fi
echo '[1/3] Capacity grid from one fixture, seed 13'
PYTHONHASHSEED=13 python -m search.spk_bv_v0u_link_pressure --reference-v0t "$reference" --out "${prefix}-13.json"
echo '[2/3] Independently re-execute capacity grid, seed 811'
PYTHONHASHSEED=811 python -m search.spk_bv_v0u_link_pressure --reference-v0t "$reference" --out "${prefix}-811.json"
echo '[3/3] Cross-process replay and pinned source bytes'
python - "${prefix}-13.json" "${prefix}-811.json" <<'PY'
import json,sys
from pathlib import Path
from spk_bv_research.paired_runs_v0o import load_json
from spk_bv_research.off_on_v0t import source_pins
from spk_bv_research.link_pressure_v0u import SCHEMA,STATUS,GRID
x,y=[load_json(Path(p)) for p in sys.argv[1:]]
if (x!=y or x.get('schema')!=SCHEMA or x.get('status')!=STATUS or
    x.get('source_sha256')!=source_pins(Path.cwd()) or
    x.get('v0t_baseline_check',{}).get('status')!='PINNED_V0T_AND_V0O_BASELINE_REPLAYED' or
    len(x.get('cells',[]))!=len(GRID)):
    raise SystemExit('SPK BV v0u native replay: REJECTED')
print(json.dumps({'status':'V0U_NATIVE_LINK_PRESSURE_REPLAY_PASS',
                  'fixture_sha256':x['original_fixture_sha256'],
                  'capacity_cells':len(x['cells']),
                  'nondominated_by_cell':[{'capacity':r['link_capacity'],
                       'policies':r['local_proxy_frontier']['nondominated']} for r in x['cells']]},sort_keys=True))
PY
echo 'SPK BV v0u LINK PRESSURE MODEL INTERVENTION: RESEARCH PASS (no physical performance or learning claim)'
