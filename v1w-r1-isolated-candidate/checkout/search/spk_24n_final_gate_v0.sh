#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Independent oracle unit tests and 729 analytical relay DAGs\n'
python -m pytest -q tests/test_spk_24n_independent_oracle_v0.py

printf '\n[2/6] True differential: frozen Network v0 against independent operational engine\n'
python -m pytest -q tests/test_spk_24n_frozen_differential_v0.py

printf '\n[3/6] Independent-process artifact equality and verification\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_24n_differential_evidence_v0 --write "$tmp/one.json"
python -m search.spk_24n_differential_evidence_v0 --write "$tmp/two.json"
cmp "$tmp/one.json" "$tmp/two.json"
python -m search.spk_24n_differential_evidence_v0 --verify "$tmp/one.json"
python -m search.spk_24n_differential_evidence_v0 --verify "$tmp/two.json"

printf '\n[4/6] Previous compiler/network observation and replay regression\n'
python -m pytest -q \
    tests/test_spk_24m_compiler_network_evidence_v0.py \
    tests/test_network_runtime_v0.py \
    tests/test_network_learning_interface_v0.py \
    tests/test_compiler_conformance_v0.py

printf '\n[5/6] Complete repository regression\n'
python -m pytest -q

printf '\n[6/6] Whitespace, frozen module preservation, and working tree\n'
git diff --check
if [[ -n "$(git diff --name-only HEAD -- spk_core spk_network spk_compiler spk_architecture)" ]]; then
    printf 'FAIL: changed tracked frozen modules\n' >&2
    exit 1
fi
if [[ -n "$(git diff --cached --name-only)" ]]; then
    printf 'FAIL: unexpected staged changes at gate\n' >&2
    git diff --cached --name-only
    exit 1
fi
python - <<'PY'
from pathlib import Path
names = (
  'search/spk_24n_independent_oracle_v0.py',
  'search/spk_24n_differential_evidence_v0.py',
  'tests/test_spk_24n_independent_oracle_v0.py',
  'tests/test_spk_24n_frozen_differential_v0.py',
  'search/spk_24n_final_gate_v0.sh',
  'docs/spk-24n-independent-differential-v0.md',
)
for n in names:
    p = Path(n)
    if not p.is_file():
        raise SystemExit('Missing 24n file: ' + n)
    data = p.read_bytes()
    if b'\r' in data or not data.endswith(b'\n') or any(
        line.endswith((b' ', b'\t')) for line in data.splitlines()
    ):
        raise SystemExit('Whitespace issue: ' + n)
print('patch whitespace: PASS')
PY
git status --short
printf '\nSPK 24n INDEPENDENT DIFFERENTIAL ORACLE GATE: PASS (declared bounded domain)\n'
