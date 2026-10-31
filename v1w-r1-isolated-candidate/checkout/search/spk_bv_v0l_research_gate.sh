#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

echo '[1/3] BV v0l native typed dossier and adversarial CLI tests'
python -m pytest -q tests/test_spk_bv_v0l_native_dossier.py

echo '[2/3] Inherited v0k entire research gate (v0i/v0j/v0k, real native source pins, frozen architecture custody)'
bash search/spk_bv_v0k_research_gate.sh

echo '[3/3] No actual v0k fixture read by this gate: run dossier CLI explicitly'
echo 'SPK BV V0l NATIVE TYPED DOSSIER: RESEARCH PASS (native-source packet bijection NOT verified)'
