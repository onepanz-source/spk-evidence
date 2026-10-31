#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Independent source-pinned negative plan and pure fault protocol\n'
python -m pytest -q \
  tests/test_spk_24v_negative_plan_v0.py \
  tests/test_spk_24v_negative_mutations_v0.py

printf '\n[2/6] Real frozen Compiler/Network admission + poisoned observer failures\n'
python -m pytest -q tests/test_spk_24v_frozen_negative_v0.py

printf '\n[3/6] Cross-process canonical audit and re-execution verification\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_24v_negative_conformance_v0 --write "$tmp/a.json"
python -m search.spk_24v_negative_conformance_v0 --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_24v_negative_conformance_v0 --verify "$tmp/a.json"
python -m search.spk_24v_negative_conformance_v0 --verify "$tmp/b.json"

printf '\n[4/6] Frozen 24o / 24t / 24u cross-layer regression\n'
python -m pytest -q \
  tests/test_spk_24o_frozen_extended_v0.py \
  tests/test_spk_24t_diagnostic_manifest_host_v0.py \
  tests/test_spk_24u_cross_layer_v0.py

printf '\n[5/6] Complete repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen boundary, staging, file and whitespace hygiene\n'
git diff --check
if [[ -n "$(git diff --name-only HEAD -- spk_core spk_network spk_compiler spk_architecture spk_simulator)" ]]; then
    echo 'FAIL: frozen/previous module change' >&2
    exit 1
fi
if [[ -n "$(git diff --cached --name-only)" ]]; then
    echo 'FAIL: unexpected staged files' >&2
    exit 1
fi
python - <<'PY'
from pathlib import Path
files = (
    'docs/spk-24v-negative-admission-observer-fault-v0.md',
    'search/spk_24v_negative_plan_v0.py',
    'search/spk_24v_negative_conformance_v0.py',
    'search/spk_24v_final_gate_v0.sh',
    'tests/test_spk_24v_negative_plan_v0.py',
    'tests/test_spk_24v_negative_mutations_v0.py',
    'tests/test_spk_24v_frozen_negative_v0.py',
)
for filename in files:
    raw = Path(filename).read_bytes()
    if (not raw.endswith(b'\n') or b'\r' in raw or
        any(line.endswith((b' ', b'\t')) for line in raw.splitlines())):
        raise SystemExit('24v patch hygiene failed: ' + filename)
print('SPK 24v structure/whitespace: PASS')
PY
git status --short
printf '\nSPK 24v NEGATIVE ADMISSION / OBSERVER FAULT: PASS (bounded injection scope)\n'
