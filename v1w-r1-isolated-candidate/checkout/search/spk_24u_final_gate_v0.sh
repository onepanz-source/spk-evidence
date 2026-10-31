#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Independent source-pinned S3-S5 conformance plan\n'
python -m pytest -q tests/test_spk_24u_conformance_plan_v0.py

printf '\n[2/6] Real frozen Compiler -> 216 three-node manifests -> 24t host and oracle\n'
python -m pytest -q tests/test_spk_24u_cross_layer_v0.py

printf '\n[3/6] Independent Python process evidence, canonical replay and fingerprints\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_24u_cross_layer_v0 --write "$tmp/a.json"
python -m search.spk_24u_cross_layer_v0 --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_24u_cross_layer_v0 --verify "$tmp/a.json"
python -m search.spk_24u_cross_layer_v0 --verify "$tmp/b.json"

printf '\n[4/6] Previous Compiler/Network/observer/host bounded regressions\n'
python -m pytest -q \
  tests/test_spk_24m_compiler_network_evidence_v0.py \
  tests/test_spk_24o_frozen_extended_v0.py \
  tests/test_spk_24p_network_application_host_v0.py \
  tests/test_spk_24t_diagnostic_manifest_host_v0.py

printf '\n[5/6] Full repository regression\n'
python -m pytest -q

printf '\n[6/6] Frozen boundaries, patch hygiene and staging\n'
git diff --check
if [[ -n "$(git diff --name-only HEAD -- spk_core spk_network spk_compiler spk_architecture spk_simulator)" ]]; then
  echo 'FAIL: frozen/previous module change' >&2
  exit 1
fi
if [[ -n "$(git diff --cached --name-only)" ]]; then
  echo 'FAIL: unexpected staged files' >&2
  exit 1
fi
python - <<'PY'
from pathlib import Path
files = (
  'docs/spk-24u-cross-layer-conformance-v0.md',
  'search/spk_24u_conformance_plan_v0.py',
  'search/spk_24u_cross_layer_v0.py',
  'search/spk_24u_final_gate_v0.sh',
  'tests/test_spk_24u_conformance_plan_v0.py',
  'tests/test_spk_24u_cross_layer_v0.py',
)
for name in files:
    p = Path(name)
    raw = p.read_bytes()
    if (not raw.endswith(b'\n') or b'\r' in raw or
            any(line.endswith((b' ', b'\t')) for line in raw.splitlines())):
        raise SystemExit('24u patch hygiene failed: ' + name)
print('SPK 24u patch structure/whitespace: PASS')
PY
git status --short
printf '\nSPK 24u CROSS-LAYER CONFORMANCE: PASS (declared finite reference scope)\n'
