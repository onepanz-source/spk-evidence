#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Finite PE service plans, 2592 independent A1b comparisons and overflow\n'
python -m pytest -q tests/test_spk_arch_a1c_service_v1c.py

printf '\n[2/6] Frozen Compiler/host against 216 x 3 x 4 capacity configurations\n'
python -m pytest -q tests/test_spk_arch_a1c_frozen_service_v1c.py

printf '\n[3/6] Independent-process sealed PE service ledger replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a1c_service_conformance_v1c --write "$tmp/a.json"
python -m search.spk_arch_a1c_service_conformance_v1c --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_arch_a1c_service_conformance_v1c --verify "$tmp/a.json"
python -m search.spk_arch_a1c_service_conformance_v1c --verify "$tmp/b.json"

printf '\n[4/6] A1a/A1b PE fabric and cross-layer frozen regression\n'
python -m pytest -q \
  tests/test_spk_arch_a1_pe_fabric_v1a.py \
  tests/test_spk_arch_a1_frozen_integration_v1a.py \
  tests/test_spk_arch_a1b_pe_execution_v1b.py \
  tests/test_spk_arch_a1b_frozen_integration_v1b.py \
  tests/test_spk_24u_cross_layer_v0.py

printf '\n[5/6] Complete repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen tags, ancestry, staging and new-code hygiene\n'
[[ $(git branch --show-current) == spk-architecture-v1 ]] || {
  echo 'FAIL: architecture branch required' >&2; exit 1;
}
tag=spk-simulator-bounded-reference-v0
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || {
  echo 'FAIL: annotated reference tag required' >&2; exit 1;
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
 'spk_architecture_v1/pe_service_v1c.py',
 'search/spk_arch_a1c_service_conformance_v1c.py',
 'search/spk_arch_a1c_final_gate_v1c.sh',
 'docs/spk-architecture-a1-pe-service-arbitration-v1c.md',
 'tests/test_spk_arch_a1c_service_v1c.py',
 'tests/test_spk_arch_a1c_frozen_service_v1c.py',
)
for path in paths:
    content = Path(path).read_bytes()
    if not content.endswith(b'\n') or b'\r' in content or any(
            line.endswith((b' ', b'\t')) for line in content.splitlines()):
        raise SystemExit('FAIL: A1c whitespace: ' + path)
staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).splitlines()
for unwanted in ('search/core_temporal_depth5_v1.py',
                 'search/core_temporal_quotient_alignment_v0.py',
                 'spk_24d_collect.py'):
    if unwanted in staged:
        raise SystemExit('FAIL: unrelated experimental file staged: ' + unwanted)
print('SPK A1c frozen source and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A1c FINITE SERVICE ARBITRATION: PASS (separate service-clock domain)\n'
