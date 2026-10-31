#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

printf '\n[1/6] Bounded release provenance policy, frozen tags and negative attestation tests\n'
python -m pytest -q tests/test_spk_24x_release_attestation_v0.py

printf '\n[2/6] End-to-end frozen Compiler, host, observer and metamorphic gates\n'
python -m pytest -q \
  tests/test_spk_24u_cross_layer_v0.py \
  tests/test_spk_24v_frozen_negative_v0.py \
  tests/test_spk_24w_frozen_metamorphic_v0.py

printf '\n[3/6] Reproducible source-pinned candidate attestation across Python processes\n'
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
python -m search.spk_24x_release_attestation_v0 --write "$tmp/a.json"
python -m search.spk_24x_release_attestation_v0 --write "$tmp/b.json"
cmp "$tmp/a.json" "$tmp/b.json"
python -m search.spk_24x_release_attestation_v0 --verify "$tmp/a.json"
python -m search.spk_24x_release_attestation_v0 --verify "$tmp/b.json"

# Reconstruct all three accepted evidence families from the real frozen chain;
# do not merely trust the digest strings embedded in the attestation.
for family in 24u 24v 24w; do
    case "$family" in
        24u) module=search.spk_24u_cross_layer_v0 ;;
        24v) module=search.spk_24v_negative_conformance_v0 ;;
        24w) module=search.spk_24w_cross_layer_metamorphic_v0 ;;
    esac
    python -m "$module" --write "$tmp/$family.json"
done
python - "$tmp" <<'PYVERIFY'
from pathlib import Path
from hashlib import sha256
import sys
from search.spk_24x_release_attestation_v0 import EVIDENCE
root = Path(sys.argv[1])
for family, reference in sorted(EVIDENCE.items()):
    value = (root / (family + '.json')).read_text(encoding='utf-8').rstrip('\n')
    digest = sha256(value.encode('utf-8')).hexdigest()
    if digest != reference['sha256']:
        raise SystemExit(f'FAIL: {family} accepted evidence drift: {digest}')
    print(f'{family} independent replay evidence sha256: PASS')
PYVERIFY

printf '\n[4/6] Isolated budget, diagnostic and observer negative regressions\n'
python -m pytest -q \
  tests/test_spk_24q_frozen_failure_parity_v0.py \
  tests/test_spk_24r_frozen_dual_limit_v0.py \
  tests/test_spk_24s_frozen_causal_failure_v0.py \
  tests/test_spk_24t_diagnostic_manifest_host_v0.py \
  tests/test_spk_24v_negative_mutations_v0.py

printf '\n[5/6] Entire repository regression\n'
python -m pytest -q

printf '\n[6/6] Source freeze, staged file, whitespace and accepted release-domain checks\n'
git diff --check
python - <<'PY'
from pathlib import Path
from search.spk_24x_release_attestation_v0 import assert_release_workspace_v0, EXPLICIT_GAPS
assert_release_workspace_v0(Path.cwd())
expected = (
    'docs/spk-24x-bounded-release-candidate-v0.md',
    'search/spk_24x_release_attestation_v0.py',
    'search/spk_24x_final_gate_v0.sh',
    'tests/test_spk_24x_release_attestation_v0.py',
)
for name in expected:
    path = Path(name)
    raw = path.read_bytes()
    if not raw.endswith(b'\n') or b'\r' in raw or any(
        line.endswith((b' ', b'\t')) for line in raw.splitlines()
    ):
        raise SystemExit('24x whitespace FAIL: ' + name)
if len(EXPLICIT_GAPS) < 5:
    raise SystemExit('24x exclusions incomplete')
print('SPK 24x bounded release candidate: patch/freeze/whitespace PASS')
PY
printf '\nSPK 24x BOUNDED SIMULATOR RELEASE CANDIDATE: PASS (no tag created)\n'
