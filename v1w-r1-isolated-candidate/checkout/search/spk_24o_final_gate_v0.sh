#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Independent primitive corpus and metamorphic algebra tests\n'
python -m pytest -q tests/test_spk_24o_semantic_corpus_v0.py

printf '\n[2/6] Frozen Network / observer / independent-oracle extended differential\n'
python -m pytest -q tests/test_spk_24o_frozen_extended_v0.py

printf '\n[3/6] Two independent process artifacts with full-corpus replay\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_24o_extended_differential_v0 --write "$tmp/a.json"
python -m search.spk_24o_extended_differential_v0 --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_24o_extended_differential_v0 --verify "$tmp/a.json"
python -m search.spk_24o_extended_differential_v0 --verify "$tmp/b.json"

printf '\n[4/6] Original 24m Compiler->Network and 24n independent regression\n'
python -m pytest -q \
    tests/test_spk_24m_compiler_network_evidence_v0.py \
    tests/test_spk_24n_independent_oracle_v0.py \
    tests/test_spk_24n_frozen_differential_v0.py \
    tests/test_compiler_conformance_v0.py \
    tests/test_network_learning_interface_v0.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Freeze boundary, workspace and patch hygiene\n'
git diff --check
if [[ -n "$(git diff --name-only HEAD -- spk_core spk_network spk_compiler spk_architecture spk_simulator)" ]]; then
    echo 'FAIL: tracked frozen or earlier simulator source modified' >&2
    exit 1
fi
if [[ -n "$(git diff --cached --name-only)" ]]; then
    echo 'FAIL: unexpected staging before acceptance' >&2
    git diff --cached --name-only
    exit 1
fi
python - <<'PY'
from pathlib import Path
files = (
    'search/spk_24o_semantic_corpus_v0.py',
    'search/spk_24o_extended_differential_v0.py',
    'search/spk_24o_final_gate_v0.sh',
    'tests/test_spk_24o_semantic_corpus_v0.py',
    'tests/test_spk_24o_frozen_extended_v0.py',
    'docs/spk-24o-extended-semantic-coverage-v0.md',
)
for item in files:
    p = Path(item)
    if not p.is_file():
        raise SystemExit('Missing 24o file: ' + item)
    data = p.read_bytes()
    if b'\r' in data or not data.endswith(b'\n') or any(
        line.endswith((b' ', b'\t')) for line in data.splitlines()
    ):
        raise SystemExit('Invalid 24o whitespace: ' + item)
print('patch whitespace: PASS')
PY
git status --short
printf '\nSPK 24o EXTENDED SEMANTIC COVERAGE GATE: PASS (216-case finite domain)\n'
