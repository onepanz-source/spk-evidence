#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

mode="${1:---preflight}"
if [[ "$mode" != "--preflight" && "$mode" != "--release" ]]; then
  echo "Usage: $0 [--preflight|--release]" >&2
  exit 2
fi

python search/compiler_v0_freeze_manifest.py --verify
python -m pytest -q tests/test_compiler_freeze_manifest_v0.py
bash search/compiler_v0_conformance_gate.sh

if [[ "$mode" == "--release" ]]; then
  # Untracked experimental files are permitted, tracked mutations are not.
  git diff --quiet HEAD -- || { echo "Tracked working tree not clean" >&2; exit 1; }
  git diff --cached --quiet || { echo "Git index not clean" >&2; exit 1; }
  temp_root="$(mktemp -d)"
  checkout="$temp_root/checkout"
  cleanup() {
    git worktree remove --force "$checkout" >/dev/null 2>&1 || true
    rm -rf -- "$temp_root"
  }
  trap cleanup EXIT
  git worktree add --detach "$checkout" HEAD
  (
    cd "$checkout"
    python search/compiler_v0_freeze_manifest.py --verify
    python -m pytest -q tests/test_compiler_freeze_manifest_v0.py
    bash search/compiler_v0_conformance_gate.sh
  )
  echo "PASS: compiler v0 clean-checkout release gate"
else
  echo "PASS: compiler v0 preflight. Commit C4, then use --release."
fi
