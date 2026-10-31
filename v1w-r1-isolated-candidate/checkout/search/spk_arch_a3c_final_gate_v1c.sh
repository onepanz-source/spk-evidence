#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] A3c PE-owned causal memory grants, reservation/actual counts and 2592+ timed runs\n'
python -m pytest -q tests/test_spk_arch_a3c_causal_memory_v1c.py

printf '\n[2/6] Frozen Compiler/host versus A3b zero-latency and A3c causal memory service\n'
python -m pytest -q tests/test_spk_arch_a3c_frozen_v1c.py

printf '\n[3/6] Independent-process source-pinned canonical A3c memory evidence\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a3c_memory_timing_conformance_v1c --write "$tmp/one.json"
python -m search.spk_arch_a3c_memory_timing_conformance_v1c --write "$tmp/two.json"
cmp "$tmp/one.json" "$tmp/two.json"
python -m search.spk_arch_a3c_memory_timing_conformance_v1c --verify "$tmp/one.json"
python -m search.spk_arch_a3c_memory_timing_conformance_v1c --verify "$tmp/two.json"

printf '\n[4/6] Previous A3a/A3b causal transport and A2c/A2d memory regressions\n'
python -m pytest -q \
  tests/test_spk_arch_a3a_temporal_transport_v1a.py \
  tests/test_spk_arch_a3b_causal_service_v1b.py \
  tests/test_spk_arch_a2c_memory_service_v1c.py \
  tests/test_spk_arch_a2d_memory_exhaustion_v1d.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen tag, architecture branch, predecessor and patch hygiene\n'
[[ $(git branch --show-current) == spk-architecture-v1 ]] || {
    echo 'FAIL: unexpected Git worktree' >&2; exit 1;
}
tag=spk-simulator-bounded-reference-v0
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || {
    echo 'FAIL: frozen reference tag is not annotated' >&2; exit 1;
}
[[ $(git rev-parse "$tag^{}") == a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]] || {
    echo 'FAIL: frozen reference moved' >&2; exit 1;
}
git merge-base --is-ancestor "$tag" HEAD
git ls-files --error-unmatch spk_architecture_v1/temporal_service_v1b.py >/dev/null
git diff --quiet "$tag" HEAD -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --cached --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --check
python - <<'PY'
from pathlib import Path
import subprocess
files = (
    'docs/spk-architecture-a3-causal-memory-v1c.md',
    'spk_architecture_v1/causal_memory_v1c.py',
    'search/spk_arch_a3c_memory_timing_conformance_v1c.py',
    'search/spk_arch_a3c_final_gate_v1c.sh',
    'tests/test_spk_arch_a3c_causal_memory_v1c.py',
    'tests/test_spk_arch_a3c_frozen_v1c.py',
)
for f in files:
    p = Path(f)
    if not p.is_file():
        raise SystemExit('FAIL: missing A3c source ' + f)
    data = p.read_bytes()
    if (not data.endswith(b'\n') or b'\r' in data
            or any(line.endswith((b' ', b'\t')) for line in data.splitlines())):
        raise SystemExit('FAIL: whitespace ' + f)
for f in subprocess.check_output(['git', 'diff', '--cached', '--name-only'],
                                 text=True).splitlines():
    if f in ('search/core_temporal_depth5_v1.py',
             'search/core_temporal_quotient_alignment_v0.py',
             'spk_24d_collect.py'):
        raise SystemExit('FAIL: unrelated research staged: ' + f)
print('SPK A3c reference freeze and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A3c CAUSAL MEMORY PERMITS: PASS (conservative transaction-envelope domain)\n'
