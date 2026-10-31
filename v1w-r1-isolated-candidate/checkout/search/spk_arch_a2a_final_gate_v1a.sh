#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Independent P/S/E/O domain admission and 648+504 PE memory projections\n'
python -m pytest -q tests/test_spk_arch_a2a_memory_v1a.py

printf '\n[2/6] Frozen Compiler/host -> actual A1d PE execution -> A2a accounting\n'
python -m pytest -q tests/test_spk_arch_a2a_frozen_v1a.py

printf '\n[3/6] Source-pinned two-process P/S/E/O canonical evidence replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a2a_memory_conformance_v1a --write "$tmp/a.json"
python -m search.spk_arch_a2a_memory_conformance_v1a --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_arch_a2a_memory_conformance_v1a --verify "$tmp/a.json"
python -m search.spk_arch_a2a_memory_conformance_v1a --verify "$tmp/b.json"

printf '\n[4/6] A1b/A1c/A1d independently executed PE regression\n'
python -m pytest -q \
  tests/test_spk_arch_a1b_pe_execution_v1b.py \
  tests/test_spk_arch_a1c_service_v1c.py \
  tests/test_spk_arch_a1d_failstop_v1d.py

printf '\n[5/6] Entire repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen v0, branch ancestry, source and patch hygiene\n'
[[ $(git branch --show-current) == spk-architecture-v1 ]] || {
  echo 'FAIL: architecture branch required' >&2; exit 1;
}
tag=spk-simulator-bounded-reference-v0
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || {
  echo 'FAIL: annotated frozen reference tag required' >&2; exit 1;
}
[[ $(git rev-parse "$tag^{}") == a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]] || {
  echo 'FAIL: frozen reference target changed' >&2; exit 1;
}
git merge-base --is-ancestor "$tag" HEAD
git diff --quiet "$tag" HEAD -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --cached --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --check
python - <<'PY'
from pathlib import Path
import subprocess
paths = (
    'docs/spk-architecture-a2-memory-domains-v1a.md',
    'spk_architecture_v1/memory_projection_v1a.py',
    'search/spk_arch_a2a_memory_conformance_v1a.py',
    'search/spk_arch_a2a_final_gate_v1a.sh',
    'tests/test_spk_arch_a2a_memory_v1a.py',
    'tests/test_spk_arch_a2a_frozen_v1a.py',
)
for path in paths:
    content = Path(path).read_bytes()
    if not content.endswith(b'\n') or b'\r' in content or any(
            line.endswith((b' ', b'\t')) for line in content.splitlines()):
        raise SystemExit('FAIL: A2a whitespace: ' + path)
staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'],
                                  text=True).splitlines()
for unwanted in ('search/core_temporal_depth5_v1.py',
                 'search/core_temporal_quotient_alignment_v0.py',
                 'spk_24d_collect.py'):
    if unwanted in staged:
        raise SystemExit('FAIL: unrelated file staged: ' + unwanted)
print('SPK A2a frozen source and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A2a LOGICAL MEMORY P/S/E/O: PASS (bounded admission and trace domain)\n'
