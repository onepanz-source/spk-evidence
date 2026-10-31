#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Actual causal PE grants: 5184 independent timed re-executions, transport conservation and denials\n'
python -m pytest -q tests/test_spk_arch_a3b_causal_service_v1b.py

printf '\n[2/6] Frozen Compiler/host against ideal A3a and finite-capacity causal PE execution\n'
python -m pytest -q tests/test_spk_arch_a3b_frozen_v1b.py

printf '\n[3/6] Two-process source-pinned A3b causal service evidence and full replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a3b_causal_service_conformance_v1b --write "$tmp/one.json"
python -m search.spk_arch_a3b_causal_service_conformance_v1b --write "$tmp/two.json"
cmp "$tmp/one.json" "$tmp/two.json"
python -m search.spk_arch_a3b_causal_service_conformance_v1b --verify "$tmp/one.json"
python -m search.spk_arch_a3b_causal_service_conformance_v1b --verify "$tmp/two.json"

printf '\n[4/6] A3a logical transport, A1c finite service and A2d memory-failure regressions\n'
python -m pytest -q \
  tests/test_spk_arch_a3a_temporal_transport_v1a.py \
  tests/test_spk_arch_a1c_service_v1c.py \
  tests/test_spk_arch_a2d_memory_exhaustion_v1d.py

printf '\n[5/6] Complete repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen v0, architecture worktree ancestry, A3a acceptance and patch hygiene\n'
[[ $(git branch --show-current) == spk-architecture-v1 ]] || {
  echo 'FAIL: expected SPK architecture worktree' >&2; exit 1;
}
tag=spk-simulator-bounded-reference-v0
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || {
  echo 'FAIL: frozen tag must be annotated' >&2; exit 1;
}
[[ $(git rev-parse "$tag^{}") == a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]] || {
  echo 'FAIL: frozen tag moved' >&2; exit 1;
}
git merge-base --is-ancestor "$tag" HEAD
git ls-files --error-unmatch spk_architecture_v1/temporal_transport_v1a.py >/dev/null
git diff --quiet "$tag" HEAD -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --cached --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --check
python - <<'PY'
from pathlib import Path
import subprocess
files = (
    'docs/spk-architecture-a3-causal-service-v1b.md',
    'spk_architecture_v1/temporal_service_v1b.py',
    'search/spk_arch_a3b_causal_service_conformance_v1b.py',
    'search/spk_arch_a3b_final_gate_v1b.sh',
    'tests/test_spk_arch_a3b_causal_service_v1b.py',
    'tests/test_spk_arch_a3b_frozen_v1b.py',
)
for filename in files:
    path = Path(filename)
    if not path.is_file():
        raise SystemExit('FAIL: missing A3b file: ' + filename)
    data = path.read_bytes()
    if (not data.endswith(b'\n') or b'\r' in data
            or any(line.endswith((b' ', b'\t')) for line in data.splitlines())):
        raise SystemExit('FAIL: invalid A3b whitespace: ' + filename)
staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'],
                                 text=True).splitlines()
for unrelated in ('search/core_temporal_depth5_v1.py',
                  'search/core_temporal_quotient_alignment_v0.py',
                  'spk_24d_collect.py'):
    if unrelated in staged:
        raise SystemExit('FAIL: unrelated research source staged: ' + unrelated)
print('SPK A3b frozen-source ancestry and archive hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A3b CAUSAL PE SERVICE GRANTS: PASS (bounded global-arbiter domain)\n'
