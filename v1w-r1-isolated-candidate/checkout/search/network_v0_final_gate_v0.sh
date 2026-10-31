#!/usr/bin/env bash

set -euo pipefail


banner() {
    printf '\n'
    printf '%s\n' \
        '======================================================================'
    printf '%s\n' "$1"
    printf '%s\n' \
        '======================================================================'
}


banner \
    'SPK NETWORK V0 FINAL FREEZE GATE'


printf '\n[1/5] Frozen Network v0 manifest\n'
python -m search.network_v0_manifest_gate


printf '\n[2/5] Frozen Core v0 dependency\n'
bash search/core_v0_final_gate_v0.sh


printf '\n[3/5] Network v0 focused regression\n'
pytest -q \
    tests/test_network_model_v0.py \
    tests/test_network_events_v0.py \
    tests/test_network_runtime_v0.py \
    tests/test_network_learning_interface_v0.py \
    tests/test_network_v0_manifest.py


printf '\n[4/5] Historical differential validation\n'
python -m search.network_v0_differential_gate


printf '\n[5/5] Full regression suite\n'
pytest -q


banner \
    'SPK NETWORK V0 FINAL FREEZE GATE: PASS'
