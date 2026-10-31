# SPK V5 T12 gate v1a, compatibility hotfix only

## Diagnosis
The original T12 gate asserted `m.get('promotion_allowed') is False` for all 23 research manifests. The historical T4ZABC and T5ABC/T5DEF/T5GHI/T5JKL manifests predate this field; `None is False` fails even when SHA custody is intact.

## Additional legacy bytecode issue
The T7ABC manifest included four Python 3.13 `__pycache__/*.pyc` files, which are ephemeral interpreter artifacts and change on regeneration. This hotfix exempts exactly those four historical cache entries, requiring their corresponding pinned Python sources to be present and correctly hashed. No other cache entry is exempt.

## Repair
This opt-in alternative launcher is additive: it does NOT modify the original T12 gate, any historical manifest, the frozen SPK source or the T12 Python bridge. It permits a missing `promotion_allowed` ONLY for the five enumerated legacy manifests. A present true or malformed value is rejected. All newer manifests MUST declare `promotion_allowed: false`. Any explicit `frozen_components_modified` / `native_learning` true is rejected. All SHA file pins and every subsequent step of the 8-stage original gate remain mandatory.

Run from the complete checkout, after T12 was installed:

```bash
bash search/spk_v5_t12_macro_native_memory_seam_gate_v1a.sh \
  ~/workspace/spk-evidence/spk-v5-t12-macro-native-memory-seam.json
```

The gate may reveal a SEPARATE original-memory API admission issue at step 4/8. Do not change original source pins or bypass that requirement. This hotfix claims only that the legacy-manifest check was incorrect, not that T12 native execution admission has passed.
