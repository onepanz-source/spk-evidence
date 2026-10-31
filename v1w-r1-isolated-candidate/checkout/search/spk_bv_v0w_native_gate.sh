#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
if [[ $# -ne 2 || "$1" != /tmp/* || "$2" != /tmp/* ]]; then
  echo 'usage: bash search/spk_bv_v0w_native_gate.sh /tmp/new-prefix /tmp/verified-v0v-native-13.json' >&2
  exit 2
fi
prefix="$1"; ref="$2"
for file in "${prefix}-13.json" "${prefix}-811.json"; do
  if [[ -e "$file" || -L "$file" ]]; then
    echo "refuse overwrite: $file" >&2; exit 2
  fi
done
if [[ ! -f "$ref" || -L "$ref" ]]; then echo 'missing/unsafe reference' >&2; exit 2; fi
echo '[1/3] Native workload 5 profiles x 3 capacity profiles x 3 controls, hash seed 13'
PYTHONHASHSEED=13 python -m search.spk_bv_v0w_workload_sensitivity --reference-v0v "$ref" --out "${prefix}-13.json"
echo '[2/3] Native replay in independent process, hash seed 811'
PYTHONHASHSEED=811 python -m search.spk_bv_v0w_workload_sensitivity --reference-v0v "$ref" --out "${prefix}-811.json"
echo '[3/3] Cross-process integrity, reference chain and scan completeness'
python - "${prefix}-13.json" "${prefix}-811.json" <<'PY'
import json,sys
from pathlib import Path
from spk_bv_research.paired_runs_v0o import load_json
from spk_bv_research.off_on_v0t import source_pins
from spk_bv_research.workload_sensitivity_v0w import SCHEMA, STATUS, WORKLOADS,CAPACITY_PROFILES
x,y=(load_json(Path(p)) for p in sys.argv[1:])
assert x==y, 'cross-process payload differs'
assert x.get('schema')==SCHEMA and x.get('status')==STATUS
assert x.get('source_sha256')==source_pins(Path.cwd())
assert x.get('same_fixture_before_after_every_run') is True
assert x.get('v0v_reference_check',{}).get('status')=='THREE_NATIVE_V0V_REFERENCE_CELLS_REPLAYED'
assert x.get('v0v_reference_check',{}).get('v0v_v0u_v0t_v0o_chain') is True
assert len(x.get('cells',[]))==len(WORKLOADS)*len(CAPACITY_PROFILES)
assert all(c.get('status')=='COMPLETE_THREE_ARM_WORKLOAD_CELL' and len(c.get('runs',{}))==3 for c in x['cells'])
print(json.dumps({'status':'BV_V0W_NATIVE_WORKLOAD_REPLAY_PASS',
                  'cells':len(x['cells']), 'executions':len(x['cells'])*3,
                  'fixture_sha256':x['original_fixture_sha256']},sort_keys=True))
PY
echo 'SPK BV v0w WORKLOAD SENSITIVITY: NATIVE REPLAY PASS (no learning benefit)'
