#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if (( $# > 1 )) || { (( $# == 1 )) && [[ "$1" != "--full" ]]; }; then
  echo 'Usage: bash search/root_frontier_nonempty_gate_v0.sh [--full]' >&2
  exit 2
fi

python -m pytest -q \
  tests/test_owned_root_frontier_nonempty_conformance_v0.py \
  tests/test_owned_root_emission_frontier_v0.py \
  tests/test_owned_external_ingress_prefix_v0.py \
  tests/test_owned_internal_state_commit_v0.py

if (( $# == 1 )); then
  python -m pytest -q
fi
