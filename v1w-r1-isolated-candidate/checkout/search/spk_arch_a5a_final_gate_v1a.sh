#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Independent A5a committed inventory and 16-phase provenance denials\n'
python -m pytest -q tests/test_spk_arch_a5a_inventory_v1a.py

printf '\n[2/6] Real frozen Compiler + A3d direct + A4d full custody vertical witnesses\n'
python -m pytest -q tests/test_spk_arch_a5a_frozen_v1a.py

printf '\n[3/6] Independent-process A5a canonical inventory/vertical evidence replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a5a_conformance_v1a --write "$tmp/one.json"
python -m search.spk_arch_a5a_conformance_v1a --write "$tmp/two.json"
cmp "$tmp/one.json" "$tmp/two.json"
python -m search.spk_arch_a5a_conformance_v1a --verify "$tmp/one.json"
python -m search.spk_arch_a5a_conformance_v1a --verify "$tmp/two.json"

printf '\n[4/6] A1a/A2d/A3d/A4d cross-stage protected regressions\n'
python -m pytest -q \
 tests/test_spk_arch_a1_pe_fabric_v1a.py \
 tests/test_spk_arch_a2d_memory_exhaustion_v1d.py \
 tests/test_spk_arch_a3d_link_backpressure_v1d.py \
 tests/test_spk_arch_a4d_state_custody_v1d.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Protected Git ancestry, committed predecessor inventory and A5a patch hygiene\n'
python - <<'PY'
from pathlib import Path
import subprocess
from spk_architecture_v1.conformance_inventory_v1a import manifest_v1a
root=Path.cwd()
manifest=manifest_v1a(root)
assert manifest['phase_count']==16 and manifest['tracked_source_files']==97
files=(
 'docs/spk-architecture-a5-vertical-conformance-v1a.md',
 'spk_architecture_v1/conformance_inventory_v1a.py',
 'search/spk_arch_a5a_conformance_v1a.py',
 'search/spk_arch_a5a_final_gate_v1a.sh',
 'tests/test_spk_arch_a5a_inventory_v1a.py',
 'tests/test_spk_arch_a5a_frozen_v1a.py',
)
for f in files:
    p=root/f
    data=p.read_bytes()
    if not data.endswith(b'\n') or b'\r' in data or any(
        r.endswith((b' ', b'\t')) for r in data.splitlines()):
        raise SystemExit('A5a dirty file '+f)
staged=set(subprocess.check_output(['git','diff','--cached','--name-only'],text=True).splitlines())
if staged:
    raise SystemExit('A5a gate requires empty staging area, found: '+repr(sorted(staged)))
print('SPK A5a Git source custody + new file hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A5a VERTICAL CONFORMANCE: PASS (stratified bounded logical domain)\n'
