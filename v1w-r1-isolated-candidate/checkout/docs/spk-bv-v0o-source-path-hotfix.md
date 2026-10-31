# SPK/* BV v0o source-path hotfix (research, 2026-10-17)

## Observed failure and scope

On fwork the `spk_bv_v0o_research_gate.sh` passed; `spk_bv_v0o_native_gate.sh` refused BEFORE fixture execution with:

```
BV v0o capture REJECTED: unsafe or missing native producer search/spk_bv_live_dual_scheduler_v0e.py
```

The original `pins()` assumed the scheduler implementation was located at that one path. It can also reside in an `spk_bv_research` package. The previous tests covered only the assumed layout. This patch fixes that *assumption*, not scheduler behavior.

## Changes

- Same target pytest test and fixture, same read-only capture and two-process checks.
- Source pin searches ONLY four explicit approved source paths: `search/spk_bv_live_dual_scheduler_v0e.py`, `spk_bv_research/live_dual_scheduler_v0e.py`, `spk_bv_research/spk_bv_live_dual_scheduler_v0e.py`, `spk_bv_live_dual_scheduler_v0e.py`.
- A single approved existing source is pinned by its SHA256 plus test-source SHA256. The attestation says `UNIQUE_APPROVED_PATH_NOT_IMPORT_PROOF`; it does NOT imply runtime import identity.
- Multiple approved existing sources: select only if the *test's direct static import* unambiguously references exactly one; otherwise fail closed. Direct import evidence is NOT execution evidence.
- Reject missing source, symlink (even if another candidate exists), directories masquerading as modules, out-of-tree files, bad digest and ambiguous candidates.
- Preserve previous synthetic fixtures without a resolution field, while new captures include one.
- No Core, Compiler, Network, Architecture v1, or source scheduler module is modified. `pins()` hashes the selected scheduler source and the targeted test before and after fixture execution.
- This is NOT a dependency-closure attestation and not a causal A/B test.

## Apply on fwork

```bash
cd ~/workspace/spk-backvalidation-v0
tar -tzf ~/Scaricati/spk-bv-v0o-source-path-hotfix.tar.gz
tar -xzf ~/Scaricati/spk-bv-v0o-source-path-hotfix.tar.gz
bash search/spk_bv_v0o_source_path_hotfix_gate.sh
bash search/spk_bv_v0o_research_gate.sh
python - <<'PY'
import json
from pathlib import Path
from spk_bv_research.paired_runs_v0o import pins
print(json.dumps(pins(Path.cwd()), sort_keys=True))
PY
bash search/spk_bv_v0o_native_gate.sh /tmp/spk-bv-v0o-native
bash search/spk_bv_credit_v0a_full_regression.sh
```

The native capture prefix cannot already exist. If it does, choose a new prefix such as `/tmp/spk-bv-v0o-native-retry` rather than deleting past evidence.

If source discovery still refuses, **do not move or copy any module** merely to satisfy the guard. Run:

```bash
find . -type f -name '*dual*scheduler*v0e*.py' -print
sed -n '1,140p' tests/test_spk_bv_live_dual_scheduler_v0e.py
```

Share only the relevant paths/imports and the exact error; a further allowlist update would need source evidence. If capture passes, share its `-inventory.json` file and gate output; do not claim equal-workload treatment parity yet.

Expected functional regression if only these 15 tests are newly collected: 3946 PASS, 6 deselected. This is an expectation, NOT a local verification of the user's full repository.
