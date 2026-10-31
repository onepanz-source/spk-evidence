#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Independent 216-case, 558-probe budget plan\n'
python -m pytest -q tests/test_spk_24q_limit_probe_plan_v0.py

printf '\n[2/6] Frozen Network / passive observer / independent failure parity\n'
python -m pytest -q tests/test_spk_24q_frozen_failure_parity_v0.py

printf '\n[3/6] Independent-process canonical failure-parity artifacts\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_24q_failure_parity_v0 --write "$tmp/a.json"
python -m search.spk_24q_failure_parity_v0 --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_24q_failure_parity_v0 --verify "$tmp/a.json"
python -m search.spk_24q_failure_parity_v0 --verify "$tmp/b.json"

printf '\n[4/6] Previous 24o and 24p bounded regressions\n'
python -m pytest -q \
  tests/test_spk_24o_semantic_corpus_v0.py \
  tests/test_spk_24o_frozen_extended_v0.py \
  tests/test_spk_24p_reference_protocol_v0.py \
  tests/test_spk_24p_network_application_host_v0.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen boundaries, staged files and patch hygiene\n'
git diff --check
if [[ -n "$(git diff --name-only HEAD -- spk_core spk_network spk_compiler spk_architecture spk_simulator)" ]]; then
  echo 'FAIL: tracked frozen code/previous simulator changed' >&2
  exit 1
fi
if [[ -n "$(git diff --cached --name-only)" ]]; then
  echo 'FAIL: unexpected staged files before 24q acceptance' >&2
  exit 1
fi
python - <<'PY'
from pathlib import Path
paths = (
    'search/spk_24q_limit_probe_plan_v0.py',
    'search/spk_24q_failure_parity_v0.py',
    'search/spk_24q_final_gate_v0.sh',
    'tests/test_spk_24q_limit_probe_plan_v0.py',
    'tests/test_spk_24q_frozen_failure_parity_v0.py',
    'docs/spk-24q-corpus-failure-parity-v0.md',
)
for name in paths:
    p = Path(name)
    if not p.is_file():
        raise SystemExit('missing 24q file: ' + name)
    content = p.read_bytes()
    if (b'\r' in content or not content.endswith(b'\n') or
            any(line.endswith((b' ', b'\t')) for line in content.splitlines())):
        raise SystemExit('bad patch whitespace: ' + name)
print('patch structure/whitespace: PASS')
PY
git status --short
printf '\nSPK 24q CORPUS-WIDE FAILURE PARITY GATE: PASS (declared bounded budget domain)\n'
