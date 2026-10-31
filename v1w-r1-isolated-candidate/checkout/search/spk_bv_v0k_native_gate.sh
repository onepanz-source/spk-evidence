#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

if [ "$#" -ne 1 ]; then
  echo 'usage: bash search/spk_bv_v0k_native_gate.sh /tmp/new-native-fixture.json' >&2
  exit 2
fi
out=$1
if [ -e "$out" ] || [ -L "$out" ]; then
  echo "REJECTED: output already exists: $out" >&2
  exit 2
fi
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT

echo '[1/5] v0h source probe: fresh SHA256 pins'
python -m search.spk_bv_v0j_probe --root . --compact > "$scratch/probe.json"
python - "$scratch/probe.json" <<'PY'
import json,sys
from pathlib import Path
from spk_bv_research.native_capture_v0k import verify_probe
pins=verify_probe(Path.cwd(),Path(sys.argv[1]))
print(json.dumps({'status':pins['status'],'source_sha256':pins['source_sha256']},sort_keys=True))
PY

echo '[2/5] Snapshot statically resolved source dependencies'
python -m search.spk_bv_v0k_dependency_census --root . > "$scratch/dependencies-before.json"

echo '[3/5] Execute pinned native pytest real_trace fixture; skip target test body'
PYTHONHASHSEED=13 python -m search.spk_bv_v0k_capture --probe "$scratch/probe.json" --out "$scratch/native-13.json"

echo '[4/5] Independent-process hashseed invariance with native fixture replay'
PYTHONHASHSEED=811 python -m search.spk_bv_v0k_capture --probe "$scratch/probe.json" --out "$scratch/native-811.json"
python - "$scratch/native-13.json" "$scratch/native-811.json" <<'PY'
import json,sys
with open(sys.argv[1]) as f:a=json.load(f)
with open(sys.argv[2]) as f:b=json.load(f)
assert a['native_fixture_sha256']==b['native_fixture_sha256'], 'native fixture differs across processes/seeds'
assert a['producer_pins']==b['producer_pins'], 'producer pins changed across captures'
print(json.dumps({'status':'PINNED_NATIVE_FIXTURE_REPRODUCIBLE',
 'fixture_sha256':a['native_fixture_sha256'],'native_v0h_verified':False},sort_keys=True))
PY

python -m search.spk_bv_v0k_dependency_census --root . > "$scratch/dependencies-after.json"
cmp "$scratch/dependencies-before.json" "$scratch/dependencies-after.json"
echo 'Native static dependency source census stable across both captures: PASS'

echo '[5/5] Publish reproducible capture outside worktree (without overwrite)'
python - "$scratch/native-13.json" "$out" <<'PY'
import pathlib,sys
src=pathlib.Path(sys.argv[1]);target=pathlib.Path(sys.argv[2]).absolute()
root=pathlib.Path.cwd()
if root==target or root in target.parents:
 raise SystemExit('REJECTED: output inside worktree')
if target.exists() or target.is_symlink():
 raise SystemExit('REJECTED: capture destination already exists')
target.parent.mkdir(parents=True,exist_ok=True)
with target.open('xb') as f: f.write(src.read_bytes())
print('CAPTURE_FILE='+str(target))
PY

echo 'SPK BV V0k NATIVE FIXTURE CAPTURE: RESEARCH PASS (packet mapping and v0h equivalence NOT verified)'
