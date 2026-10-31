#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] A2a pre-execution admission, P/S/E/O shortfalls and A2c service exhaustion\n'
python -m pytest -q tests/test_spk_arch_a2d_memory_exhaustion_v1d.py

printf '\n[2/6] Frozen Compiler/host -> A1d -> A2a/A2b/A2c -> A2d exact and short boundaries\n'
python -m pytest -q tests/test_spk_arch_a2d_frozen_v1d.py

printf '\n[3/6] Independent-process canonical memory-failure evidence + full replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a2d_exhaustion_conformance_v1d --write "$tmp/a.json"
python -m search.spk_arch_a2d_exhaustion_conformance_v1d --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_arch_a2d_exhaustion_conformance_v1d --verify "$tmp/a.json"
python -m search.spk_arch_a2d_exhaustion_conformance_v1d --verify "$tmp/b.json"

printf '\n[4/6] A2a capacity, A2b authority and A2c service bounded regressions\n'
python -m pytest -q \
  tests/test_spk_arch_a2a_memory_v1a.py \
  tests/test_spk_arch_a2b_access_v1b.py \
  tests/test_spk_arch_a2c_memory_service_v1c.py

printf '\n[5/6] Complete repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen reference, ancestry, staging and patch hygiene\n'
[[ $(git branch --show-current) == spk-architecture-v1 ]] || {
  echo 'FAIL: architecture worktree branch required' >&2; exit 1;
}
tag=spk-simulator-bounded-reference-v0
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || {
  echo 'FAIL: frozen annotated reference required' >&2; exit 1;
}
[[ $(git rev-parse "$tag^{}") == a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]] || {
  echo 'FAIL: frozen v0 tag moved' >&2; exit 1;
}
git merge-base --is-ancestor "$tag" HEAD
git diff --quiet "$tag" HEAD -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --cached --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --check
python - <<'PY'
from pathlib import Path
import subprocess
files = (
 'docs/spk-architecture-a2-memory-exhaustion-v1d.md',
 'spk_architecture_v1/memory_exhaustion_v1d.py',
 'search/spk_arch_a2d_exhaustion_conformance_v1d.py',
 'search/spk_arch_a2d_final_gate_v1d.sh',
 'tests/test_spk_arch_a2d_memory_exhaustion_v1d.py',
 'tests/test_spk_arch_a2d_frozen_v1d.py',
)
for path in files:
    p = Path(path)
    if not p.is_file():
        raise SystemExit('FAIL: A2d missing ' + path)
    raw = p.read_bytes()
    if (not raw.endswith(b'\n') or b'\r' in raw
            or any(s.endswith((b' ', b'\t')) for s in raw.splitlines())):
        raise SystemExit('FAIL: A2d whitespace ' + path)
staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'],
                                 text=True).splitlines()
for unwanted in ('search/core_temporal_depth5_v1.py',
                 'search/core_temporal_quotient_alignment_v0.py',
                 'spk_24d_collect.py'):
    if unwanted in staged:
        raise SystemExit('FAIL: unrelated experiment staged: ' + unwanted)
print('SPK A2d source freeze and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A2d MEMORY RESOURCE EXHAUSTION: PASS (bounded preflight + aggregate-service domain)\n'
