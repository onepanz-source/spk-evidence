#!/usr/bin/env bash
# SPK BV v0o static-import custody hotfix test gate. Read-only relative to frozen source trees.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
python -m pytest --version >/dev/null || { echo 'python -m pytest unavailable: activate the SPK virtualenv' >&2; exit 2; }
echo '[1/3] Original BV v0o research regressions'
python -m pytest -q tests/test_spk_bv_v0o_paired_runs.py
echo '[2/3] Prior source-path hotfix regressions'
python -m pytest -q tests/test_spk_bv_v0o_source_paths_hotfix.py
echo '[3/3] Bounded static native import closure and adversarial regressions'
python -m pytest -q tests/test_spk_bv_v0o_ast_source_resolution.py
echo 'SPK BV v0o STATIC IMPORT SOURCE CUSTODY HOTFIX: LOCAL PASS (not a real native fixture capture)'
