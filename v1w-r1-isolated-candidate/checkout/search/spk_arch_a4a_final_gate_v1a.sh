#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] A4a operating-mode authority, quiescent epoch and 648 live/replay pairs\n'
python -m pytest -q tests/test_spk_arch_a4a_operating_modes_v1a.py

printf '\n[2/6] Real Compiler/host versus A3d inside mode-controlled execution\n'
python -m pytest -q tests/test_spk_arch_a4a_frozen_v1a.py

printf '\n[3/6] Source-pinned A4a canonical evidence, independent-process full replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a4a_mode_conformance_v1a --write "$tmp/one.json"
python -m search.spk_arch_a4a_mode_conformance_v1a --write "$tmp/two.json"
cmp "$tmp/one.json" "$tmp/two.json"
python -m search.spk_arch_a4a_mode_conformance_v1a --verify "$tmp/one.json"
python -m search.spk_arch_a4a_mode_conformance_v1a --verify "$tmp/two.json"

printf '\n[4/6] A3d causal backpressure and A3c memory prior regressions\n'
python -m pytest -q \
  tests/test_spk_arch_a3d_link_backpressure_v1d.py \
  tests/test_spk_arch_a3c_causal_memory_v1c.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen reference, branch, A3d checkpoint and patch hygiene\n'
[[ $(git branch --show-current) == spk-architecture-v1 ]] || {
    echo 'FAIL: unexpected architecture branch' >&2; exit 1;
}
tag=spk-simulator-bounded-reference-v0
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || {
    echo 'FAIL: frozen reference tag not annotated' >&2; exit 1;
}
[[ $(git rev-parse "$tag^{}") == a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]] || {
    echo 'FAIL: frozen reference moved' >&2; exit 1;
}
git merge-base --is-ancestor "$tag" HEAD
git ls-files --error-unmatch spk_architecture_v1/causal_transport_v1d.py >/dev/null
git diff --quiet "$tag" HEAD -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --cached --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --check
python - <<'PY'
from pathlib import Path
import subprocess
files = (
    'docs/spk-architecture-a4-operating-modes-v1a.md',
    'spk_architecture_v1/operating_modes_v1a.py',
    'search/spk_arch_a4a_mode_conformance_v1a.py',
    'search/spk_arch_a4a_final_gate_v1a.sh',
    'tests/test_spk_arch_a4a_operating_modes_v1a.py',
    'tests/test_spk_arch_a4a_frozen_v1a.py',
)
for f in files:
    p = Path(f)
    if not p.is_file():
        raise SystemExit('FAIL: missing A4a source ' + f)
    data = p.read_bytes()
    if (not data.endswith(b'\n') or b'\r' in data
            or any(x.endswith((b' ', b'\t')) for x in data.splitlines())):
        raise SystemExit('FAIL: A4a whitespace ' + f)
for f in subprocess.check_output(['git', 'diff', '--cached', '--name-only'],
                                  text=True).splitlines():
    if f in ('search/core_temporal_depth5_v1.py',
             'search/core_temporal_quotient_alignment_v0.py',
             'spk_24d_collect.py'):
        raise SystemExit('FAIL: unrelated research staged ' + f)
print('SPK A4a frozen-source and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A4a MODE AUTHORITY: PASS (trusted quiescent logical epochs)\n'
