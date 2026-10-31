#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] A4d quiescent P/S/E/O snapshots, 648 replay reconstructions, stale-state denials\n'
python -m pytest -q tests/test_spk_arch_a4d_state_custody_v1d.py

printf '\n[2/6] Frozen Compiler/host, A4c promotion authority and A4d cold reset custody\n'
python -m pytest -q tests/test_spk_arch_a4d_frozen_v1d.py

printf '\n[3/6] Two-process source-pinned canonical state custody and cold activation evidence\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a4d_custody_conformance_v1d --write "$tmp/one.json"
python -m search.spk_arch_a4d_custody_conformance_v1d --write "$tmp/two.json"
cmp "$tmp/one.json" "$tmp/two.json"
python -m search.spk_arch_a4d_custody_conformance_v1d --verify "$tmp/one.json"
python -m search.spk_arch_a4d_custody_conformance_v1d --verify "$tmp/two.json"

printf '\n[4/6] A4c candidate verification, A4b mode memory and A4a authority regressions\n'
python -m pytest -q \
  tests/test_spk_arch_a4c_candidate_promotion_v1c.py \
  tests/test_spk_arch_a4b_mode_memory_v1b.py \
  tests/test_spk_arch_a4a_operating_modes_v1a.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen reference, branch, A4c predecessor and patch hygiene\n'
[[ $(git branch --show-current) == spk-architecture-v1 ]] || { echo 'FAIL: branch' >&2; exit 1; }
tag=spk-simulator-bounded-reference-v0
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || { echo 'FAIL: annotated tag' >&2; exit 1; }
[[ $(git rev-parse "$tag^{}") == a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]] || { echo 'FAIL: frozen baseline drift' >&2; exit 1; }
git merge-base --is-ancestor "$tag" HEAD
git ls-files --error-unmatch spk_architecture_v1/candidate_promotion_v1c.py >/dev/null
git diff --quiet "$tag" HEAD -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --cached --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --check
python - <<'PY'
from pathlib import Path
import subprocess
files=(
 'docs/spk-architecture-a4-state-custody-v1d.md',
 'spk_architecture_v1/state_custody_v1d.py',
 'search/spk_arch_a4d_custody_conformance_v1d.py',
 'search/spk_arch_a4d_final_gate_v1d.sh',
 'tests/test_spk_arch_a4d_state_custody_v1d.py',
 'tests/test_spk_arch_a4d_frozen_v1d.py',
)
for f in files:
    data=Path(f).read_bytes()
    if not data.endswith(b'\n') or b'\r' in data or any(
        row.endswith((b' ',b'\t')) for row in data.splitlines()):
        raise SystemExit('FAIL: dirty or missing A4d file '+f)
for f in subprocess.check_output(['git','diff','--cached','--name-only'],text=True).splitlines():
    if f in ('search/core_temporal_depth5_v1.py',
             'search/core_temporal_quotient_alignment_v0.py','spk_24d_collect.py'):
        raise SystemExit('FAIL: unrelated staged file '+f)
print('SPK A4d frozen-source and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A4d QUIESCENT STATE CUSTODY: PASS (trusted replay recovery and cold reset domain)\n'
