#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
echo '[1/3] BV v0o original research regressions (unchanged)'
python -m pytest -q tests/test_spk_bv_v0o_paired_runs.py
echo '[2/3] Corrected native-source paths, ambiguity, symlink and capture regression'
python -m pytest -q tests/test_spk_bv_v0o_source_paths_hotfix.py
echo '[3/3] Existing Architecture v1 guard is exercised by the inherited v0o gate, separately'
echo 'SPK BV v0o SOURCE-PATH HOTFIX: LOCAL TEST PASS (real fwork capture still separate)'
