# SPK BV v0o: native producer import-custody hotfix

## Trigger / verified failure

`pins(Path.cwd())` previously refused the real research worktree with:

`PairError: native scheduler producer not found at approved paths`

The earlier hotfix enumerated four hypothesized Python module paths, none of which necessarily matches the actual module imported by `tests/test_spk_bv_live_dual_scheduler_v0e.py`.

## Narrow correction

Only `spk_bv_research/paired_runs_v0o.py` is replaced. If none of the four legacy-approved module paths is present, `pins()` now parses the **actual test source** as an AST and resolves in-repository `spk_*` and `search` Python modules through absolute and bounded relative imports, including their statically reachable transitive closure. It pins SHA-256 digests for the test and each identified source file. The module code is not imported or executed during this provenance step.

Safety boundaries: reject unreadable/non-regular files, symlinks or symlinked parent components, ambiguous module-file / package-file resolution, unparsable sources, import closure above 96 files, source files above 600 KB, and absence of any concrete non-`__init__` in-tree import. Attestation validation rejects arbitrary paths. The legacy single approved module behavior is preserved.

The result explicitly reports `STATIC_LOCAL_IMPORT_CLOSURE_NOT_RUNTIME_PROOF`. AST reachability is **not** proof of actual runtime module identity, import resolution, completeness of dynamically loaded sources, equal ON/OFF workload, nor causal measurement.

## Apply / validate on fwork

Run from `~/workspace/spk-backvalidation-v0` with the original SPK virtualenv active:

```bash
source ~/workspace/spk-algebra/.venv/bin/activate
python -m pytest --version

tar -tzf ~/Scaricati/spk-bv-v0o-import-custody-hotfix.tar.gz
tar -xzf ~/Scaricati/spk-bv-v0o-import-custody-hotfix.tar.gz
bash search/spk_bv_v0o_import_custody_hotfix_gate.sh
bash search/spk_bv_v0o_research_gate.sh
```

Inspect actual source pins **before** attempting the capture:

```bash
python - <<'PY'
import json
from pathlib import Path
from spk_bv_research.paired_runs_v0o import pins
print(json.dumps(pins(Path.cwd()), indent=2, sort_keys=True))
PY
```

If the pins succeed, use a fresh, never-used prefix:

```bash
bash search/spk_bv_v0o_native_gate.sh /tmp/spk-bv-v0o-native-importfix
```

Upload/share only `/tmp/spk-bv-v0o-native-importfix-inventory.json` and the textual gate output for further investigation. Do not assert controlled ON/OFF equivalence without a verified workload witness.

If imports are dynamically built or the test does not reference a concrete in-tree module, the source pin deliberately fails closed. Inspect the actual test file and import references; do not disable custody. This hotfix neither edits frozen Architecture v1 sources nor repairs Python environment activation.

## Local verification

39 original v0o tests, 15 prior hotfix tests, 12 new adversarial static-import tests: 66 PASS in an isolated local project scaffold. The full inherited Architecture v1 gate and real fwork fixture must be run independently on fwork.
