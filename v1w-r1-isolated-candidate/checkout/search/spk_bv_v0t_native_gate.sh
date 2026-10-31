#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
if [[ $# -ne 2 || "$1" != /tmp/* ]]; then
  echo 'usage: bash search/spk_bv_v0t_native_gate.sh /tmp/new-prefix /tmp/existing-v0o-capture-13.json' >&2
  exit 2
fi
prefix="$1"
reference="$2"
if [[ ! -f "$reference" || -L "$reference" ]]; then echo "reference must be regular existing file" >&2;exit 2;fi
for x in "${prefix}-13.json" "${prefix}-811.json"; do
  if [[ -e "$x" || -L "$x" ]]; then echo "refuse overwrite: $x" >&2;exit 2;fi
done
echo '[1/3] Native OFF, ON-forward-first, ON-feedback-first (PYTHONHASHSEED=13)'
PYTHONHASHSEED=13 python -m search.spk_bv_v0t_three_arm --out "${prefix}-13.json" --reference-v0o "$reference"
echo '[2/3] Independent process replay (PYTHONHASHSEED=811)'
PYTHONHASHSEED=811 python -m search.spk_bv_v0t_three_arm --out "${prefix}-811.json" --reference-v0o "$reference"
echo '[3/3] Source, input, run and deltas equality across independent processes'
python - "${prefix}-13.json" "${prefix}-811.json" <<'PY'
import json,sys
from pathlib import Path
from spk_bv_research.paired_runs_v0o import load_json
from spk_bv_research.off_on_v0t import SCHEMA,STATUS,source_pins
x,y=(load_json(Path(name)) for name in sys.argv[1:])
if (x!=y or x.get('schema')!=SCHEMA or x.get('status')!=STATUS or
    x.get('producer_source_sha256')!=source_pins(Path.cwd()) or
    x.get('v0o_reference_check',{}).get('status')!='PINNED_V0O_ON_RUNS_REPLAYED_IN_THREE_ARM'):
    raise SystemExit('SPK BV v0t native replay mismatch: REJECTED')
print(json.dumps({'status':'NATIVE_THREE_ARM_REPLAY_PASS',
                  'shared_fixture_input_sha256':x['shared_fixture_input_sha256'],
                  'off_to_on_forward_first':x['interventions']['toggle_enabled_only'],
                  'forward_to_feedback_first':x['interventions']['change_priority_only']},sort_keys=True))
PY
echo 'SPK BV v0t THREE-ARM NATIVE MODEL INTERVENTION: RESEARCH PASS (no learning, hardware or global benefit claim)'
