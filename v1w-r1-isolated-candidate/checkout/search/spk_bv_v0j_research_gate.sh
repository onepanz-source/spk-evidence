#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

echo '[1/5] BV v0j native-provenance mapping and idealized pressure tests'
python -m pytest -q tests/test_spk_bv_v0j_native_pressure.py

echo '[2/5] Inherited BV v0i evidence/transport contract tests'
python -m pytest -q tests/test_spk_bv_evidence_cost_v0i.py

echo '[3/5] Independent-process and hashseed-invariant synthetic witness'
t1=$(mktemp); t2=$(mktemp)
trap 'rm -f "$t1" "$t2"' EXIT
PYTHONHASHSEED=13 python -m search.spk_bv_v0j_witness > "$t1"
PYTHONHASHSEED=811 python -m search.spk_bv_v0j_witness > "$t2"
cmp "$t1" "$t2"
cat "$t1"

echo '[4/5] Native producer static API discovery (no import/execution)'
python -m search.spk_bv_v0j_probe --root . --compact | python -c '
import json,sys
x=json.load(sys.stdin)
assert x["schema"]=="spk-bv-native-source-probe/v0j"
print(json.dumps({"status":x["status"],"files_scanned":x["files_scanned"],"scan_truncated":x["scan_truncated"]},sort_keys=True))'

echo '[5/5] Frozen Architecture v1 package path guard'
python - <<'PY'
import subprocess
from pathlib import Path
tag='spk-architecture-bounded-reference-v1'
if subprocess.run(['git','rev-parse','-q','--verify',f'refs/tags/{tag}^{{commit}}'],
                  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
    raise SystemExit('FAIL: frozen Architecture v1 tag unavailable')
paths=[p for p in ('spk_core','spk_network','spk_compiler','spk_simulator','spk_architecture') if Path(p).is_dir()]
changed=subprocess.check_output(['git','diff','--name-only',tag,'--',*paths],text=True).strip() if paths else ''
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--',*paths],text=True).strip() if paths else ''
if changed or untracked:
    raise SystemExit(f'FAIL: frozen package paths changed: {changed} {untracked}')
print('Frozen Architecture v1 package paths: PASS (run inherited full guard separately)')
PY

echo 'SPK BV V0j NATIVE PROVENANCE / CAPACITY PROBES: RESEARCH PASS (native v0h mapping pending)'
