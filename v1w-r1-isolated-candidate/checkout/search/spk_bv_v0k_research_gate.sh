#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

echo '[1/5] BV v0k source pins, lossless typed capture, adversarial fixture and CLI tests'
python -m pytest -q tests/test_spk_bv_v0k_native_capture.py

echo '[2/5] Inherited BV v0i and v0j research regression'
python -m pytest -q tests/test_spk_bv_evidence_cost_v0i.py tests/test_spk_bv_v0j_native_pressure.py

echo '[3/5] Source probe bound to native BV v0h actual files (not a native trace replay)'
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
python -m search.spk_bv_v0j_probe --root . --compact > "$tmp"
python - "$tmp" <<'PY'
import json,sys
from pathlib import Path
from spk_bv_research.native_capture_v0k import verify_probe
p=verify_probe(Path.cwd(),Path(sys.argv[1]))
print(json.dumps({'status':p['status'],'source_sha256':p['source_sha256']},sort_keys=True))
PY

echo '[4/5] AST dependency discovery including native modules missed by filename probe'
python -m search.spk_bv_v0k_dependency_census --root . | python -c 'import json,sys;d=json.load(sys.stdin);assert d["files_scanned"]>=2;print(json.dumps({"status":d["status"],"files_scanned":d["files_scanned"]},sort_keys=True))'
echo '[5/5] Frozen Architecture v1 package path guard'
python - <<'PY'
from pathlib import Path
import subprocess
name='spk-architecture-bounded-reference-v1'
if subprocess.run(['git','rev-parse','-q','--verify',f'refs/tags/{name}^{{commit}}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
    raise SystemExit('FAIL: frozen Architecture v1 tag missing')
paths=[p for p in ('spk_core','spk_network','spk_compiler','spk_simulator','spk_architecture') if Path(p).is_dir()]
if paths:
    staged=subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],text=True).strip()
    tracked=subprocess.check_output(['git','diff','--name-only',name,'--',*paths],text=True).strip()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--',*paths],text=True).strip()
    if staged or tracked or untracked:
        raise SystemExit('FAIL: frozen source changes detected: '+str((staged,tracked,untracked)))
print('Frozen Architecture v1 tracked and untracked package guard: PASS')
PY

echo 'SPK BV V0k SOURCE-BOUND CAPTURE: RESEARCH GATE PASS (native fixture capture requires separate command)'
