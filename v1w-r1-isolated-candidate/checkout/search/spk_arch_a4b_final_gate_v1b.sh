#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Mode-scoped P/S/E/O authority, priority and 648 EXECUTE/VERIFY service pairs\n'
python -m pytest -q tests/test_spk_arch_a4b_mode_memory_v1b.py

printf '\n[2/6] Frozen Compiler/host A4a and A2b cross-witness mode memory integration\n'
python -m pytest -q tests/test_spk_arch_a4b_frozen_v1b.py

printf '\n[3/6] Independent-process sealed mode-memory evidence and canonical replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a4b_mode_memory_conformance_v1b --write "$tmp/one.json"
python -m search.spk_arch_a4b_mode_memory_conformance_v1b --write "$tmp/two.json"
cmp "$tmp/one.json" "$tmp/two.json"
python -m search.spk_arch_a4b_mode_memory_conformance_v1b --verify "$tmp/one.json"
python -m search.spk_arch_a4b_mode_memory_conformance_v1b --verify "$tmp/two.json"

printf '\n[4/6] A4a controller and A2b/A2c logical memory regressions\n'
python -m pytest -q \
  tests/test_spk_arch_a4a_operating_modes_v1a.py \
  tests/test_spk_arch_a2b_access_v1b.py \
  tests/test_spk_arch_a2c_memory_service_v1c.py

printf '\n[5/6] Complete repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen tag, ancestry, prior A4a checkpoint and new-source hygiene\n'
[[ $(git branch --show-current) == spk-architecture-v1 ]] || {
  echo 'FAIL: unexpected architecture branch' >&2; exit 1;
}
tag=spk-simulator-bounded-reference-v0
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || {
  echo 'FAIL: missing annotated v0 tag' >&2; exit 1;
}
[[ $(git rev-parse "$tag^{}") == a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]] || {
  echo 'FAIL: v0 baseline changed' >&2; exit 1;
}
git merge-base --is-ancestor "$tag" HEAD
git ls-files --error-unmatch spk_architecture_v1/operating_modes_v1a.py >/dev/null
git diff --quiet "$tag" HEAD -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --cached --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --check
python - <<'PY'
from pathlib import Path
import subprocess
files = (
    'docs/spk-architecture-a4-mode-memory-v1b.md',
    'spk_architecture_v1/mode_memory_v1b.py',
    'search/spk_arch_a4b_mode_memory_conformance_v1b.py',
    'search/spk_arch_a4b_final_gate_v1b.sh',
    'tests/test_spk_arch_a4b_mode_memory_v1b.py',
    'tests/test_spk_arch_a4b_frozen_v1b.py',
)
for f in files:
    data = Path(f).read_bytes()
    if (not data.endswith(b'\n') or b'\r' in data
            or any(line.endswith((b' ', b'\t')) for line in data.splitlines())):
        raise SystemExit('FAIL: missing/dirty A4b file ' + f)
for f in subprocess.check_output(['git', 'diff', '--cached', '--name-only'],
                                  text=True).splitlines():
    if f in ('search/core_temporal_depth5_v1.py',
             'search/core_temporal_quotient_alignment_v0.py',
             'spk_24d_collect.py'):
        raise SystemExit('FAIL: unrelated research staged ' + f)
print('SPK A4b frozen-source and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A4b MODE MEMORY AUTHORITY: PASS (trusted logical replay scope)\n'
