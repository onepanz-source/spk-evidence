#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] All 648 independent architecture metamorphic cases and denials\n'
python -m pytest -q tests/test_spk_arch_a5b_metamorphic_v1b.py

printf '\n[2/6] Frozen Compiler/host ideal witnesses plus committed A5a provenance\n'
python -m pytest -q tests/test_spk_arch_a5b_frozen_v1b.py

printf '\n[3/6] Two-process source-pinned canonical metamorphic replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a5b_conformance_v1b --write "$tmp/one.json"
python -m search.spk_arch_a5b_conformance_v1b --write "$tmp/two.json"
cmp "$tmp/one.json" "$tmp/two.json"
python -m search.spk_arch_a5b_conformance_v1b --verify "$tmp/one.json"
python -m search.spk_arch_a5b_conformance_v1b --verify "$tmp/two.json"

printf '\n[4/6] A5a vertical, A4d custody, A3d transport protected regressions\n'
python -m pytest -q \
 tests/test_spk_arch_a5a_inventory_v1a.py \
 tests/test_spk_arch_a4d_state_custody_v1d.py \
 tests/test_spk_arch_a3d_link_backpressure_v1d.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen source, 17 committed predecessor phases and new-source hygiene\n'
python - <<'PY'
from pathlib import Path
import subprocess
from search.spk_arch_a5b_conformance_v1b import predecessor_v1b
root=Path.cwd()
p=predecessor_v1b(root)
assert p['predecessor_phases']==17 and p['predecessor_files']==103
new=(
 'docs/spk-architecture-a5-metamorphic-conformance-v1b.md',
 'spk_architecture_v1/metamorphic_v1b.py',
 'search/spk_arch_a5b_conformance_v1b.py',
 'search/spk_arch_a5b_final_gate_v1b.sh',
 'tests/test_spk_arch_a5b_metamorphic_v1b.py',
 'tests/test_spk_arch_a5b_frozen_v1b.py',
)
for f in new:
    path=root/f
    data=path.read_bytes()
    if not data.endswith(b'\n') or b'\r' in data or any(
            x.endswith((b' ',b'\t')) for x in data.splitlines()):
        raise SystemExit('dirty A5b file: '+f)
if subprocess.check_output(['git','diff','--cached','--name-only'],text=True).strip():
    raise SystemExit('A5b gate requires no staged files')
print('SPK A5b frozen predecessors and new-source hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A5b METAMORPHIC CONFORMANCE: PASS (bounded ordering-preserving domain)\n'
