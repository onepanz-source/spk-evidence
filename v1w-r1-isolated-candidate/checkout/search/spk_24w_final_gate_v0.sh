#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Independent 216 x 3 graph-isomorphism oracle and source-pin proofs\n'
python -m pytest -q tests/test_spk_24w_metamorphic_plan_v0.py

printf '\n[2/6] Frozen Compiler -> 648 renamed/permuted manifests -> 24t host + observer + oracle\n'
python -m pytest -q tests/test_spk_24w_frozen_metamorphic_v0.py

printf '\n[3/6] Reproducible full-corpus artifacts and replay across independent processes\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_24w_cross_layer_metamorphic_v0 --write "$tmp/a.json"
python -m search.spk_24w_cross_layer_metamorphic_v0 --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_24w_cross_layer_metamorphic_v0 --verify "$tmp/a.json"
python -m search.spk_24w_cross_layer_metamorphic_v0 --verify "$tmp/b.json"

printf '\n[4/6] Previous 24u/24v compiled and negative observer regressions\n'
python -m pytest -q \
  tests/test_spk_24u_conformance_plan_v0.py \
  tests/test_spk_24u_cross_layer_v0.py \
  tests/test_spk_24v_negative_plan_v0.py \
  tests/test_spk_24v_frozen_negative_v0.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen modules, staging, archive structure and patch hygiene\n'
git diff --check
if [[ -n "$(git diff --name-only HEAD -- spk_core spk_network spk_compiler spk_architecture spk_simulator)" ]]; then
    echo 'FAIL: frozen source or prior module modified' >&2
    exit 1
fi
if [[ -n "$(git diff --cached --name-only)" ]]; then
    echo 'FAIL: staged files must be empty before 24w acceptance' >&2
    exit 1
fi
python - <<'PY'
from pathlib import Path
expected = (
    'docs/spk-24w-structural-metamorphic-conformance-v0.md',
    'search/spk_24w_metamorphic_plan_v0.py',
    'search/spk_24w_cross_layer_metamorphic_v0.py',
    'search/spk_24w_final_gate_v0.sh',
    'tests/test_spk_24w_metamorphic_plan_v0.py',
    'tests/test_spk_24w_frozen_metamorphic_v0.py',
)
for name in expected:
    path = Path(name)
    raw = path.read_bytes()
    if not raw.endswith(b'\n') or b'\r' in raw or any(
            line.endswith((b' ', b'\t')) for line in raw.splitlines()):
        raise SystemExit('24w patch hygiene FAIL: '+name)
print('SPK 24w patch structure/whitespace: PASS')
PY
git status --short
printf '\nSPK 24w CROSS-LAYER STRUCTURAL METAMORPHIC CONFORMANCE: PASS (bounded isomorphism domain)\n'
