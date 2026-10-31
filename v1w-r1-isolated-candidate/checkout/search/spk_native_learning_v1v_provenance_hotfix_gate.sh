#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
printf '[hotfix 1/3] Exact-hash upgrade of research v1v exception contract
'
PYTHONPATH=. python3 hotfix/v1v/apply.py
printf '[hotfix 2/3] Independent fail-closed negative exception tests
'
PYTHONPATH=. python3 -m pytest -q hotfix/v1v/test_v1v_exception_contract.py
printf '[hotfix 3/3] Complete original v1v eight-stage release gate (unchanged)
'
bash search/spk_native_learning_v1v_sensed_context_macro_gate.sh "$@"
