#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] PE-local compute, 648 independent differential tests and ownership\n'
python -m pytest -q tests/test_spk_arch_a1b_pe_execution_v1b.py

printf '\n[2/6] Real frozen Compiler, manifest host and PE-local runtime\n'
python -m pytest -q tests/test_spk_arch_a1b_frozen_integration_v1b.py

printf '\n[3/6] Independent-process PE-local/compiled-host canonical evidence replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a1b_pe_local_v1b --write "$tmp/a.json"
python -m search.spk_arch_a1b_pe_local_v1b --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_arch_a1b_pe_local_v1b --verify "$tmp/a.json"
python -m search.spk_arch_a1b_pe_local_v1b --verify "$tmp/b.json"

printf '\n[4/6] A1a + pre-release Compiler-host cross-layer regression\n'
python -m pytest -q tests/test_spk_arch_a1_pe_fabric_v1a.py \
  tests/test_spk_arch_a1_frozen_integration_v1a.py \
  tests/test_spk_24u_cross_layer_v0.py

printf '\n[5/6] Complete repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen v0 tag, branch ancestry, source and patch hygiene\n'
tag=spk-simulator-bounded-reference-v0
[[ $(git branch --show-current) == spk-architecture-v1 ]] || {
 echo 'FAIL: architecture branch required' >&2; exit 1;
}
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || {
 echo 'FAIL: annotated v0 release tag required' >&2; exit 1;
}
[[ $(git rev-parse "$tag^{}") == a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]] || {
 echo 'FAIL: frozen release target mismatch' >&2; exit 1;
}
git merge-base --is-ancestor "$tag" HEAD
git diff --quiet "$tag" HEAD -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --cached --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --check
python - <<'PY'
from pathlib import Path
files = (
 'spk_architecture_v1/pe_execution_v1b.py',
 'search/spk_arch_a1b_pe_local_v1b.py',
 'search/spk_arch_a1b_final_gate_v1b.sh',
 'docs/spk-architecture-a1-pe-local-execution-v1b.md',
 'tests/test_spk_arch_a1b_pe_execution_v1b.py',
 'tests/test_spk_arch_a1b_frozen_integration_v1b.py',
)
for path in files:
    b = Path(path).read_bytes()
    if not b.endswith(b'\n') or b'\r' in b or any(
            ln.endswith((b' ', b'\t')) for ln in b.splitlines()):
        raise SystemExit('FAIL: A1b whitespace: ' + path)
for path in ('search/core_temporal_depth5_v1.py',
             'search/core_temporal_quotient_alignment_v0.py',
             'spk_24d_collect.py'):
    if Path(path).is_file() and path in __import__('subprocess').check_output(
            ['git', 'diff', '--cached', '--name-only'], text=True).splitlines():
        raise SystemExit('FAIL: unrelated experimental file staged: ' + path)
print('SPK A1b v0 frozen source and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A1b PE-LOCAL EXECUTION GATE: PASS (ideal logical PE domain)\n'
