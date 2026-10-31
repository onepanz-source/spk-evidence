#!/usr/bin/env bash
# Full functional regression in research branch, excluding ONLY six historical
# committed-release custody tests hard-pinned to branch spk-architecture-v1.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD${PYTHONPATH:+$PYTHONPATH}"
if [ "$(git branch --show-current)" != 'spk-backvalidation-v0' ]; then
  echo 'ERROR: requires spk-backvalidation-v0 research branch' >&2
  exit 3
fi
base=spk-architecture-bounded-reference-v1
test "$(git rev-parse "$base^{commit}")" = '5af99cd1f4d603bf0c8e1557a6561c107765fdb5'
echo 'Research worktree: full functional suite, six inherited Git branch-specific release custody tests explicitly deselected.'
python -m pytest -q \
  --deselect=tests/test_spk_arch_a5a_frozen_v1a.py::test_prior_committed_16_phase_git_inventory \
  --deselect=tests/test_spk_arch_a5b_frozen_v1b.py::test_a5a_seventeen_phase_git_provenance \
  --deselect=tests/test_spk_arch_a5c_frozen_v1c.py::test_eighteen_predecessor_phases_committed \
  --deselect=tests/test_spk_arch_a5d_frozen_v1d.py::test_frozen_source_and_nineteen_prior_certifications \
  --deselect=tests/test_spk_arch_a5d_release_v1d.py::test_actual_committed_clean_release_inventory \
  --deselect=tests/test_spk_arch_a5d_release_v1d.py::test_manifest_refuses_dirty_a5c_source
echo 'Research full functional regression: PASS (6 archived branch-custody checks intentionally excluded)'
