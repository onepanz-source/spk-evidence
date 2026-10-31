#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Independent simultaneous-limit prefix proofs across corpus\n'
python -m pytest -q tests/test_spk_24r_dual_limit_plan_v0.py

printf '\n[2/6] Frozen dual-limit behavior and passive-observer invariance\n'
python -m pytest -q tests/test_spk_24r_frozen_dual_limit_v0.py

printf '\n[3/6] Reproducible characterization artifacts across Python processes\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_24r_dual_limit_characterization_v0 --write "$tmp/a.json"
python -m search.spk_24r_dual_limit_characterization_v0 --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_24r_dual_limit_characterization_v0 --verify "$tmp/a.json"
python -m search.spk_24r_dual_limit_characterization_v0 --verify "$tmp/b.json"

printf '\n[4/6] Previous budget and host reference regression\n'
python -m pytest -q \
  tests/test_spk_24q_limit_probe_plan_v0.py \
  tests/test_spk_24q_frozen_failure_parity_v0.py \
  tests/test_spk_24p_network_application_host_v0.py \
  tests/test_spk_24p_reference_protocol_v0.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen source, worktree and patch hygiene\n'
git diff --check
if [[ -n "$(git diff --name-only HEAD -- spk_core spk_network spk_compiler spk_architecture spk_simulator)" ]]; then
  echo 'FAIL: modifications of frozen source or prior simulator' >&2
  exit 1
fi
if [[ -n "$(git diff --cached --name-only)" ]]; then
  echo 'FAIL: unexpected staged files' >&2
  exit 1
fi
python - <<'PY'
from pathlib import Path
paths = (
    'docs/spk-24r-simultaneous-budget-characterization-v0.md',
    'search/spk_24r_dual_limit_plan_v0.py',
    'search/spk_24r_dual_limit_characterization_v0.py',
    'search/spk_24r_final_gate_v0.sh',
    'tests/test_spk_24r_dual_limit_plan_v0.py',
    'tests/test_spk_24r_frozen_dual_limit_v0.py',
)
for filename in paths:
    path = Path(filename)
    if not path.is_file():
        raise SystemExit('missing 24r file: ' + filename)
    data = path.read_bytes()
    if (b'\r' in data or not data.endswith(b'\n') or
            any(line.endswith((b' ', b'\t')) for line in data.splitlines())):
        raise SystemExit('24r patch whitespace failure: ' + filename)
print('24r patch structure/whitespace: PASS')
PY
git status --short
printf '\nSPK 24r SIMULTANEOUS BUDGET CHARACTERIZATION: PASS (bounded observational scope)\n'
