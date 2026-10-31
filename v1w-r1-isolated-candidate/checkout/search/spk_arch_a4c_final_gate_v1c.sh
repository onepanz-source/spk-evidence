#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] A4c trusted cold staging, independent candidate replay, approval, CAS and 648 program changes\n'
python -m pytest -q tests/test_spk_arch_a4c_candidate_promotion_v1c.py

printf '\n[2/6] Frozen Compiler/host A4b baseline plus independently compiled candidate promotion witness\n'
python -m pytest -q tests/test_spk_arch_a4c_frozen_v1c.py

printf '\n[3/6] Source-pinned two-process promotion and cold activation replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a4c_candidate_conformance_v1c --write "$tmp/one.json"
python -m search.spk_arch_a4c_candidate_conformance_v1c --write "$tmp/two.json"
cmp "$tmp/one.json" "$tmp/two.json"
python -m search.spk_arch_a4c_candidate_conformance_v1c --verify "$tmp/one.json"
python -m search.spk_arch_a4c_candidate_conformance_v1c --verify "$tmp/two.json"

printf '\n[4/6] A4b mode memory, A4a modes and A3d transport regressions\n'
python -m pytest -q \
  tests/test_spk_arch_a4b_mode_memory_v1b.py \
  tests/test_spk_arch_a4a_operating_modes_v1a.py \
  tests/test_spk_arch_a3d_link_backpressure_v1d.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen tag, worktree ancestry, A4b acceptance and patch hygiene\n'
[[ $(git branch --show-current) == spk-architecture-v1 ]] || {
  echo 'FAIL: wrong architecture branch' >&2; exit 1;
}
tag=spk-simulator-bounded-reference-v0
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || {
  echo 'FAIL: missing frozen annotated tag' >&2; exit 1;
}
[[ $(git rev-parse "$tag^{}") == a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]] || {
  echo 'FAIL: frozen baseline drift' >&2; exit 1;
}
git merge-base --is-ancestor "$tag" HEAD
git ls-files --error-unmatch spk_architecture_v1/mode_memory_v1b.py >/dev/null
git diff --quiet "$tag" HEAD -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --cached --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --check
python - <<'PY'
from pathlib import Path
import subprocess
files = (
    'docs/spk-architecture-a4-candidate-promotion-v1c.md',
    'spk_architecture_v1/candidate_promotion_v1c.py',
    'search/spk_arch_a4c_candidate_conformance_v1c.py',
    'search/spk_arch_a4c_final_gate_v1c.sh',
    'tests/test_spk_arch_a4c_candidate_promotion_v1c.py',
    'tests/test_spk_arch_a4c_frozen_v1c.py',
)
for f in files:
    data=Path(f).read_bytes()
    if not data.endswith(b'\n') or b'\r' in data or any(
        row.endswith((b' ',b'\t')) for row in data.splitlines()):
        raise SystemExit('FAIL: dirty or absent A4c file '+f)
for f in subprocess.check_output(['git','diff','--cached','--name-only'],text=True).splitlines():
    if f in ('search/core_temporal_depth5_v1.py',
             'search/core_temporal_quotient_alignment_v0.py', 'spk_24d_collect.py'):
        raise SystemExit('FAIL: unrelated research staged '+f)
print('SPK A4c frozen-source and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A4c CONTROLLED COLD CANDIDATE PROMOTION: PASS (trusted logical pointer domain)\n'
