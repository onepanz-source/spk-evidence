#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] BV v1m native posthoc projection, original and variant trace guards'
python -m pytest -q tests/test_spk_bv_v1m_native_passive_projection.py
python -m compileall -q spk_bv_research/native_passive_trace_projection_v1m.py search/spk_bv_v1m_native_passive_projection.py
echo '[2/3] Inherited v1l source-bound lab + frozen Architecture v1 custody'
bash search/spk_bv_v1l_research_gate.sh
echo '[3/3] Live native trace projection requires separate CLI'
echo 'SPK BV v1m PASS (test contract only; native trace replay separate)'
