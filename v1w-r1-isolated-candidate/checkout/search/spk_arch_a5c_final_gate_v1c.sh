#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] A5c real A3d/A4a/A4d adversarial denials and 648 source cases\n'
python -m pytest -q tests/test_spk_arch_a5c_adversarial_v1c.py

printf '\n[2/6] Frozen Compiler/host plus A5b committed predecessor provenance\n'
python -m pytest -q tests/test_spk_arch_a5c_frozen_v1c.py

printf '\n[3/6] Source-pinned two-process canonical adversarial evidence replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a5c_adversarial_conformance_v1c --write "$tmp/one.json"
python -m search.spk_arch_a5c_adversarial_conformance_v1c --write "$tmp/two.json"
cmp "$tmp/one.json" "$tmp/two.json"
python -m search.spk_arch_a5c_adversarial_conformance_v1c --verify "$tmp/one.json"
python -m search.spk_arch_a5c_adversarial_conformance_v1c --verify "$tmp/two.json"

printf '\n[4/6] A5b metamorphic, A5a provenance and A4d custody regressions\n'
python -m pytest -q \
 tests/test_spk_arch_a5b_metamorphic_v1b.py \
 tests/test_spk_arch_a5a_inventory_v1a.py \
 tests/test_spk_arch_a4d_state_custody_v1d.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen reference, 18 committed predecessor phases and patch hygiene\n'
python - <<'PY'
from pathlib import Path
import subprocess
from search.spk_arch_a5c_adversarial_conformance_v1c import predecessor_v1c
root=Path.cwd()
p=predecessor_v1c(root)
assert p['predecessor_phases']==18 and p['predecessor_files']==109
files=(
 'docs/spk-architecture-a5-adversarial-boundaries-v1c.md',
 'spk_architecture_v1/adversarial_boundaries_v1c.py',
 'search/spk_arch_a5c_adversarial_conformance_v1c.py',
 'search/spk_arch_a5c_final_gate_v1c.sh',
 'tests/test_spk_arch_a5c_adversarial_v1c.py',
 'tests/test_spk_arch_a5c_frozen_v1c.py',
)
for f in files:
    data=(root/f).read_bytes()
    if (not data.endswith(b'\n') or b'\r' in data or any(
            x.endswith((b' ',b'\t')) for x in data.splitlines())):
        raise SystemExit('dirty A5c file: '+f)
if subprocess.check_output(['git','diff','--cached','--name-only'],text=True).strip():
    raise SystemExit('A5c gate requires no staged files')
print('SPK A5c frozen predecessors and new-file hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A5c ADVERSARIAL BOUNDARIES: PASS (trusted logical fault domain)\n'
