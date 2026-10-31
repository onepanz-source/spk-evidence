#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Actual PE-local fail-stop, quiescent prefixes and capacity-invariance\n'
python -m pytest -q tests/test_spk_arch_a1d_failstop_v1d.py

printf '\n[2/6] Real frozen Compiler/host versus A1d nominal runs and fault prefixes\n'
python -m pytest -q tests/test_spk_arch_a1d_frozen_conformance_v1d.py

printf '\n[3/6] Independent-process source-pinned canonical fail-stop evidence\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a1d_fault_conformance_v1d --write "$tmp/a.json"
python -m search.spk_arch_a1d_fault_conformance_v1d --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_arch_a1d_fault_conformance_v1d --verify "$tmp/a.json"
python -m search.spk_arch_a1d_fault_conformance_v1d --verify "$tmp/b.json"

printf '\n[4/6] A1a/A1b/A1c and frozen cross-layer regressions\n'
python -m pytest -q \
  tests/test_spk_arch_a1_pe_fabric_v1a.py \
  tests/test_spk_arch_a1_frozen_integration_v1a.py \
  tests/test_spk_arch_a1b_pe_execution_v1b.py \
  tests/test_spk_arch_a1b_frozen_integration_v1b.py \
  tests/test_spk_arch_a1c_service_v1c.py \
  tests/test_spk_arch_a1c_frozen_service_v1c.py

printf '\n[5/6] Complete repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen tags, worktree ancestry, staging and patch hygiene\n'
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
    'spk_architecture_v1/pe_fault_v1d.py',
    'search/spk_arch_a1d_fault_conformance_v1d.py',
    'search/spk_arch_a1d_final_gate_v1d.sh',
    'docs/spk-architecture-a1-pe-failstop-v1d.md',
    'tests/test_spk_arch_a1d_failstop_v1d.py',
    'tests/test_spk_arch_a1d_frozen_conformance_v1d.py',
)
for path in paths:
    content = Path(path).read_bytes()
    if not content.endswith(b'\n') or b'\r' in content or any(
            line.endswith((b' ', b'\t')) for line in content.splitlines()):
        raise SystemExit('FAIL: A1d whitespace: ' + path)
staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).splitlines()
for unwanted in ('search/core_temporal_depth5_v1.py',
                 'search/core_temporal_quotient_alignment_v0.py',
                 'spk_24d_collect.py'):
    if unwanted in staged:
        raise SystemExit('FAIL: unrelated file staged: ' + unwanted)
print('SPK A1d frozen source and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A1d PE FAIL-STOP QUIESCENCE: PASS (synchronous pre-grant fault domain)\n'
