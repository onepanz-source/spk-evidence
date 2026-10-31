#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Causal sender outboxes, bandwidth grants and lossless backpressure\n'
python -m pytest -q tests/test_spk_arch_a3d_link_backpressure_v1d.py

printf '\n[2/6] Frozen Compiler/host versus ideal A3c and actual A3d link congestion\n'
python -m pytest -q tests/test_spk_arch_a3d_frozen_v1d.py

printf '\n[3/6] Two-process source-pinned canonical A3d backpressure evidence\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a3d_link_conformance_v1d --write "$tmp/one.json"
python -m search.spk_arch_a3d_link_conformance_v1d --write "$tmp/two.json"
cmp "$tmp/one.json" "$tmp/two.json"
python -m search.spk_arch_a3d_link_conformance_v1d --verify "$tmp/one.json"
python -m search.spk_arch_a3d_link_conformance_v1d --verify "$tmp/two.json"

printf '\n[4/6] A3c memory permits, A3b PE grants and A3a transport regressions\n'
python -m pytest -q \
    tests/test_spk_arch_a3c_causal_memory_v1c.py \
    tests/test_spk_arch_a3b_causal_service_v1b.py \
    tests/test_spk_arch_a3a_temporal_transport_v1a.py

printf '\n[5/6] Complete repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen v0, branch ancestry, predecessor and A3d patch hygiene\n'
[[ $(git branch --show-current) == spk-architecture-v1 ]] || {
    echo 'FAIL: unexpected architecture branch' >&2; exit 1;
}
tag=spk-simulator-bounded-reference-v0
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || {
    echo 'FAIL: frozen tag not annotated' >&2; exit 1;
}
[[ $(git rev-parse "$tag^{}") == a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]] || {
    echo 'FAIL: frozen reference moved' >&2; exit 1;
}
git merge-base --is-ancestor "$tag" HEAD
git ls-files --error-unmatch spk_architecture_v1/causal_memory_v1c.py >/dev/null
git diff --quiet "$tag" HEAD -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --cached --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --check
python - <<'PY'
from pathlib import Path
import subprocess
files = (
    'docs/spk-architecture-a3-causal-backpressure-v1d.md',
    'spk_architecture_v1/causal_transport_v1d.py',
    'search/spk_arch_a3d_link_conformance_v1d.py',
    'search/spk_arch_a3d_final_gate_v1d.sh',
    'tests/test_spk_arch_a3d_link_backpressure_v1d.py',
    'tests/test_spk_arch_a3d_frozen_v1d.py',
)
for f in files:
    p = Path(f)
    if not p.is_file():
        raise SystemExit('FAIL: missing A3d source ' + f)
    data = p.read_bytes()
    if (not data.endswith(b'\n') or b'\r' in data
            or any(x.endswith((b' ', b'\t')) for x in data.splitlines())):
        raise SystemExit('FAIL: A3d whitespace ' + f)
for f in subprocess.check_output(['git', 'diff', '--cached', '--name-only'],
                                  text=True).splitlines():
    if f in ('search/core_temporal_depth5_v1.py',
             'search/core_temporal_quotient_alignment_v0.py',
             'spk_24d_collect.py'):
        raise SystemExit('FAIL: unrelated research staged: ' + f)
print('SPK A3d frozen-source and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A3d CAUSAL TRANSPORT BACKPRESSURE: PASS (bounded sender-FIFO logical link domain)\n'
