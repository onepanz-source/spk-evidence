#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '[1/3] v1y.1 frozen snapshot SHA parity, lossless typed result, and trace restoration'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1y_native_external_probe.py
python -m compileall -q spk_bv_research/native_external_probe_v1y.py tests/test_spk_bv_v1y_native_external_probe.py
echo '[2/3] v1x native-baseline contract regression'
python -m pytest -q --import-mode=importlib tests/test_spk_bv_v1x_reference_observation_port.py
echo '[3/3] inherited v1y source/Architecture custody research gate'
bash search/spk_bv_v1y_research_gate.sh
echo 'SPK BV v1y.1 SHA PARITY HOTFIX: RESEARCH PASS (native probe attestation via separate CLI)'
