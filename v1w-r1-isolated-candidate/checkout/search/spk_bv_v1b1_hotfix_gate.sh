#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
echo '[1/3] v1b.1 native instruction syntax shape and adversarial controls'
python -m pytest -q tests/test_spk_bv_v1b_native_operator_replay.py
python -m compileall -q spk_bv_research/native_operator_replay_v1b.py search/spk_bv_v1b_native_operator_replay.py
python - <<'PY'
import json
from spk_bv_research.native_operator_replay_v1b import shape
class Neuron:
    instructions = ('load', ('add', 1), {'op': 'emit', 'channel': 7})
r=shape(Neuron())
assert r['instruction_count']==3
assert [x['representation'] for x in r['instruction_shapes']]==['str', 'tuple', 'dict']
assert r['instruction_codec']=='strict-v0k-lossless-canonical-fixture'
print(json.dumps({'instruction_codec':r['instruction_codec'],'supported_demo_shapes':[x['representation'] for x in r['instruction_shapes']]},sort_keys=True))
PY
echo '[2/3] Full inherited v1b research gate, frozen architecture guard remains inherited'
bash search/spk_bv_v1b_research_gate.sh
echo '[3/3] Real fwork native microtrace still requires separate read-only CLI'
echo 'SPK BV v1b.1 NATIVE INSTRUCTION SHAPE HOTFIX: RESEARCH PASS (native run separate)'
