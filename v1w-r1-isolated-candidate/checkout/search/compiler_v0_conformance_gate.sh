#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Gate C3: the existing public C1/C2 tests, independent C3 oracle tests,
# and the full repository regression suite. No source mutation.
python -m pytest -q \
  tests/test_compile_pipeline_v0.py \
  tests/test_compilation_manifest_v0.py \
  tests/test_compiler_conformance_v0.py
python -m pytest -q
