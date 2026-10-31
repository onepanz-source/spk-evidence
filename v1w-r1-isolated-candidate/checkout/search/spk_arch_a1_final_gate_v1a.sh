#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] PE placement pure contract, ownership and route multiplicity\n'
python -m pytest -q tests/test_spk_arch_a1_pe_fabric_v1a.py

printf '\n[2/6] Frozen Compiler + PE admission + manifest + reference host\n'
python -m pytest -q tests/test_spk_arch_a1_frozen_integration_v1a.py

printf '\n[3/6] Canonical 216x3 placement evidence, independent-process replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a1_pe_fabric_v1a --write "$tmp/a.json"
python -m search.spk_arch_a1_pe_fabric_v1a --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_arch_a1_pe_fabric_v1a --verify "$tmp/a.json"
python -m search.spk_arch_a1_pe_fabric_v1a --verify "$tmp/b.json"

printf '\n[4/6] Previous 24u/24w Compiler-host cross-layer regression\n'
python -m pytest -q tests/test_spk_24u_cross_layer_v0.py tests/test_spk_24w_frozen_metamorphic_v0.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen tags, worktree ancestry, no source modifications, hygiene\n'
tag=spk-simulator-bounded-reference-v0
if [[ $(git branch --show-current) != spk-architecture-v1 ]]; then
  echo 'FAIL: expected isolated architecture branch' >&2; exit 1
fi
if [[ $(git cat-file -t "refs/tags/$tag") != tag ]]; then
  echo 'FAIL: annotated simulator reference tag required' >&2; exit 1
fi
if [[ $(git rev-parse "$tag^{}") != a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]]; then
  echo 'FAIL: reference tag target mismatch' >&2; exit 1
fi
git merge-base --is-ancestor "$tag" HEAD
git diff --quiet "$tag" HEAD -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --cached --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --check
python - <<'PY'
from pathlib import Path
files = (
 'spk_architecture_v1/__init__.py',
 'spk_architecture_v1/pe_fabric_v1a.py',
 'search/spk_arch_a1_pe_fabric_v1a.py',
 'search/spk_arch_a1_final_gate_v1a.sh',
 'tests/test_spk_arch_a1_pe_fabric_v1a.py',
 'tests/test_spk_arch_a1_frozen_integration_v1a.py',
 'docs/spk-architecture-a1-pe-fabric-v1a.md',
)
for path in files:
    raw = Path(path).read_bytes()
    if not raw.endswith(b'\n') or b'\r' in raw or any(
         line.endswith((b' ', b'\t')) for line in raw.splitlines()):
        raise SystemExit('FAIL: whitespace: ' + path)
print('SPK A1a reference freeze + patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A1a PE FABRIC PLACEMENT CONFORMANCE: PASS (static mapping domain)\n'
