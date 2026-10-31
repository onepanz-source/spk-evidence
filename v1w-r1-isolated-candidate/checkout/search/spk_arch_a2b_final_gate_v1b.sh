#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Independently authorized P/S/E/O access rights on 648 closed and 504 fault prefixes\n'
python -m pytest -q tests/test_spk_arch_a2b_access_v1b.py

printf '\n[2/6] Real frozen Compiler, A1d execution, A2a memory and A2b access control\n'
python -m pytest -q tests/test_spk_arch_a2b_frozen_v1b.py

printf '\n[3/6] Reproducible controller authorization evidence and replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a2b_access_conformance_v1b --write "$tmp/a.json"
python -m search.spk_arch_a2b_access_conformance_v1b --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_arch_a2b_access_conformance_v1b --verify "$tmp/a.json"
python -m search.spk_arch_a2b_access_conformance_v1b --verify "$tmp/b.json"

printf '\n[4/6] A2a accounting and A1d fail-stop regression\n'
python -m pytest -q \
  tests/test_spk_arch_a2a_memory_v1a.py \
  tests/test_spk_arch_a1d_failstop_v1d.py

printf '\n[5/6] Entire repository regression\n'
python -m pytest -q

printf '\n[6/6] Immutable reference, architecture branch, staging, patch hygiene\n'
[[ $(git branch --show-current) == spk-architecture-v1 ]] || {
  echo 'FAIL: architecture branch required' >&2; exit 1;
}
tag=spk-simulator-bounded-reference-v0
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || {
  echo 'FAIL: annotated simulator reference tag required' >&2; exit 1;
}
[[ $(git rev-parse "$tag^{}") == a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]] || {
  echo 'FAIL: frozen simulator tag target moved' >&2; exit 1;
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
    'docs/spk-architecture-a2-memory-access-v1b.md',
    'spk_architecture_v1/memory_access_v1b.py',
    'search/spk_arch_a2b_access_conformance_v1b.py',
    'search/spk_arch_a2b_final_gate_v1b.sh',
    'tests/test_spk_arch_a2b_access_v1b.py',
    'tests/test_spk_arch_a2b_frozen_v1b.py',
)
for path in paths:
    content = Path(path).read_bytes()
    if (not content.endswith(b'\n') or b'\r' in content
            or any(line.endswith((b' ', b'\t')) for line in content.splitlines())):
        raise SystemExit('FAIL: A2b whitespace: ' + path)
staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).splitlines()
for unwanted in ('search/core_temporal_depth5_v1.py',
                 'search/core_temporal_quotient_alignment_v0.py',
                 'spk_24d_collect.py'):
    if unwanted in staged:
        raise SystemExit('FAIL: unrelated experimental file staged: ' + unwanted)
print('SPK A2b frozen source and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A2b LOGICAL MEMORY AUTHORIZATION: PASS (bounded logical access domain)\n'
