#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pytest -q tests/test_spk_bv_v0p_policy_identity.py
python - <<'PY'
from pathlib import Path
import subprocess
import sys
root=Path.cwd().resolve()
if not (root/'spk_bv_research/policy_identity_v0p.py').is_file(): raise SystemExit('missing new module')
# Use existing frozen tracked source guard; this gate does not duplicate inherited gate.
print('BV v0p local test gate: PASS; run inherited v0o research gate and independent native CLI separately')
PY
