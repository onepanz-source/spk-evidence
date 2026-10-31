#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Independent A2b-authorized P/S/E/O capacity and service policy\n'
python -m pytest -q tests/test_spk_arch_a2c_memory_service_v1c.py

printf '\n[2/6] Frozen Compiler/host to A1d/A2a/A2b to finite A2c memory service\n'
python -m pytest -q tests/test_spk_arch_a2c_frozen_v1c.py

printf '\n[3/6] Cross-process canonical service attestation and full replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_arch_a2c_memory_service_conformance_v1c --write "$tmp/a.json"
python -m search.spk_arch_a2c_memory_service_conformance_v1c --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_arch_a2c_memory_service_conformance_v1c --verify "$tmp/a.json"
python -m search.spk_arch_a2c_memory_service_conformance_v1c --verify "$tmp/b.json"

printf '\n[4/6] A2b access rights, A2a projection and A1c service regressions\n'
python -m pytest -q \
  tests/test_spk_arch_a2b_access_v1b.py \
  tests/test_spk_arch_a2a_memory_v1a.py \
  tests/test_spk_arch_a1c_service_v1c.py

printf '\n[5/6] Complete repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen reference, architecture branch, archive and whitespace hygiene\n'
[[ $(git branch --show-current) == spk-architecture-v1 ]] || {
  echo 'FAIL: architecture branch required' >&2; exit 1;
}
tag=spk-simulator-bounded-reference-v0
[[ $(git cat-file -t "refs/tags/$tag") == tag ]] || {
  echo 'FAIL: frozen annotated reference required' >&2; exit 1;
}
[[ $(git rev-parse "$tag^{}") == a76ebaae49373a4c6b66f94465d78dbf1cf19f80 ]] || {
  echo 'FAIL: frozen tag moved' >&2; exit 1;
}
git merge-base --is-ancestor "$tag" HEAD
git diff --quiet "$tag" HEAD -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --cached --quiet -- spk_core spk_network spk_compiler spk_simulator spk_architecture
git diff --check
python - <<'PY'
from pathlib import Path
import subprocess
files = (
 'docs/spk-architecture-a2-memory-service-v1c.md',
 'spk_architecture_v1/memory_service_v1c.py',
 'search/spk_arch_a2c_memory_service_conformance_v1c.py',
 'search/spk_arch_a2c_final_gate_v1c.sh',
 'tests/test_spk_arch_a2c_memory_service_v1c.py',
 'tests/test_spk_arch_a2c_frozen_v1c.py',
)
for path in files:
    if not Path(path).is_file():
        raise SystemExit('FAIL: A2c missing '+path)
    content = Path(path).read_bytes()
    if not content.endswith(b'\n') or b'\r' in content or any(
        x.endswith((b' ', b'\t')) for x in content.splitlines()
    ):
        raise SystemExit('FAIL: A2c whitespace '+path)
staged = subprocess.check_output(['git','diff','--cached','--name-only'],text=True).splitlines()
for unwanted in ('search/core_temporal_depth5_v1.py',
                 'search/core_temporal_quotient_alignment_v0.py',
                 'spk_24d_collect.py'):
    if unwanted in staged:
        raise SystemExit('FAIL: unrelated experiment staged: '+unwanted)
print('SPK A2c source freeze and patch hygiene: PASS')
PY
printf '\nSPK ARCHITECTURE A2c MEMORY SERVICE ARBITRATION: PASS (bounded aggregate-demand domain)\n'
