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
    'SPK CORE V0 FINAL FREEZE GATE'


printf '\n[1/5] Frozen semantic manifest\n'
python -m search.core_v0_manifest_gate


printf '\n[2/5] Frozen Core IR fingerprint\n'
python -m search.core_v0_ir_fingerprint


printf '\n[3/5] Runtime normal-form final gate\n'
bash search/core_phase3_final_gate_v0.sh


printf '\n[4/5] DOMAIN premises / rule soundness\n'
bash search/core_domain_premises_final_gate_v0.sh


printf '\n[5/5] Full regression suite\n'
pytest -q


banner \
    'SPK CORE V0 FINAL FREEZE GATE: PASS'
