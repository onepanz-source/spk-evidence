#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] A3a independent PE-local causal transport, 1944 timed runs and analytical paths\n'
python -m pytest -q tests/test_spk_arch_a3a_temporal_transport_v1a.py

printf '\n[2/6] Real frozen Compiler/host versus 648 ideal transported networks, positive latency characterization\n'
python -m pytest -q tests/test_spk_arch_a3a_frozen_v1a.py

printf '\n[3/6] Source-pinned independently replayed canonical A3a evidence\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a3a_temporal_conformance_v1a --write "$tmp/one.json"
python -m search.spk_arch_a3a_temporal_conformance_v1a --write "$tmp/two.json"
cmp "$tmp/one.json" "$tmp/two.json"
python -m search.spk_arch_a3a_temporal_conformance_v1a --verify "$tmp/one.json"
python -m search.spk_arch_a3a_temporal_conformance_v1a --verify "$tmp/two.json"

printf '\n[4/6] A1b exact PE reference and A2d memory-failure regressions\n'
python -m pytest -q tests/test_spk_arch_a1b_pe_execution_v1b.py tests/test_spk_arch_a2d_memory_exhaustion_v1d.py

printf '\n[5/6] Complete repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen v0, branch ancestry, A2d acceptance, staging and patch hygiene\n'
[[ $(git branch --show-current) == spk-architecture-v1 ]] || {
  echo 'FAIL: architecture worktree branch required' >&2; exit 1;
}
tag=spk-simulator-bounded-reference-v0
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || {
  echo 'FAIL: annotated frozen tag missing' >&2; exit 1;
}
[[ $(git rev-parse "$tag^{}") == a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]] || {
  echo 'FAIL: frozen tag moved' >&2; exit 1;
}
git merge-base --is-ancestor "$tag" HEAD
git ls-files --error-unmatch spk_architecture_v1/memory_exhaustion_v1d.py >/dev/null
git diff --quiet "$tag" HEAD -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --cached --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --check
python - <<'PY'
from pathlib import Path
import subprocess
files = (
    'docs/spk-architecture-a3-causal-transport-v1a.md',
    'spk_architecture_v1/temporal_transport_v1a.py',
    'search/spk_arch_a3a_temporal_conformance_v1a.py',
    'search/spk_arch_a3a_final_gate_v1a.sh',
    'tests/test_spk_arch_a3a_temporal_transport_v1a.py',
    'tests/test_spk_arch_a3a_frozen_v1a.py',
)
for filename in files:
    path = Path(filename)
    if not path.is_file():
        raise SystemExit('FAIL: A3a file absent: ' + filename)
    data = path.read_bytes()
    if (not data.endswith(b'\n') or b'\r' in data
            or any(line.endswith((b' ', b'\t')) for line in data.splitlines())):
        raise SystemExit('FAIL: A3a whitespace: ' + filename)
staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'],
                                 text=True).splitlines()
for unwanted in ('search/core_temporal_depth5_v1.py',
                 'search/core_temporal_quotient_alignment_v0.py',
                 'spk_24d_collect.py'):
    if unwanted in staged:
        raise SystemExit('FAIL: unrelated experiment staged')
print('SPK A3a source freeze and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A3a CAUSAL TRANSPORT: PASS (bounded logical transport domain)\n'
