#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pytest -q tests/test_spk_bv_v1a_symbolic_holdout.py
python -m compileall -q spk_bv_research/symbolic_holdout_v1a.py search/spk_bv_v1a_symbolic_holdout.py
printf '%s\n' 'SPK BV v1a SYMBOLIC HOLDOUT RESEARCH PASS (no native learning claim)'
