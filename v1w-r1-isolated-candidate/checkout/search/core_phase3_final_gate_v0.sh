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
    'SPK CORE PHASE 3 NORMAL-FORM FINAL GATE v0'


printf '\n[1/6] Runtime normal-form / idempotence\n'
python -m search.core_phase3_runtime_nf_v0


printf '\n[2/6] Structural/semantic pass-cycle census\n'
python -m search.core_phase3_pass_cycle_census_v0


printf '\n[3/6] Exact phase-aware cycle gate\n'
python -m search.core_phase3_cycle_exact_provenance_v0


printf '\n[4/6] Runtime helper-fork joinability\n'
python -m search.core_phase3_runtime_fork_joinability_v0


printf '\n[5/6] Runtime NF irreducibility\n'
python -m search.core_phase3_runtime_irreducible_nf_v0


printf '\n[6/6] Full regression suite\n'
pytest -q


banner \
    'SPK CORE PHASE 3 FINAL GATE: PASS'
