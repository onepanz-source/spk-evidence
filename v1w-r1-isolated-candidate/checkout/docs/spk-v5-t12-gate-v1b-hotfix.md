# SPK T12 preflight hotfix v1b

This hotfix fixes **`T7ABC_CACHE_EXCEPTIONS_DRIFT`** in the T12 v1a preflight.

The v1a launcher asserted the *exact set* of four historical `.pyc` cache paths. The T7ABC historical manifest may enumerate a different number of those derived cache artifacts, even where its Python sources and their SHA-256 pins are valid. The fixed-set assertion is therefore not a valid release invariant.

The v1b gate:

* Preserves the historical-schema compatibility fix for older `promotion_allowed`-absent manifests. Explicit promotion or native-learning claims remain forbidden.
* Does not assume an exact number or list of T7ABC `.pyc` entries. Only bytecode cache entries **inside the historical T7ABC package**, under `__pycache__`, with a conventional Python cache filename, are excluded from byte-level pinning.
* For **each** excluded cache, requires its corresponding `.py` source to be present in the same historical manifest. All those `.py` files and every other non-cache file still undergo normal SHA-256 verification. Unexpected cache entries in other manifests fail closed.
* Preserves original source SHA checks, original-memory-API admission acceptance, 23 full regression suites, independent report regeneration, native-learning nonpromotion and immutable report publication.
* Does not modify T7ABC, T12 code, original source, previous launchers, historical manifests, or evidence. This is **not** a new milestone.

The previous extraction printed an mtime warning because v1a tar members had a future timestamp. This v1b archive has normalized historical mtimes to avoid that unrelated warning.

Execute from the repository root:

```bash
cd ~/workspace/spk-backvalidation-v0
tar --skip-old-files -xzf ~/Scaricati/SPK_V5_T12_Gate_Historical_Manifest_Compatibility_Hotfix_v1b_20261023.tar.gz
bash search/spk_v5_t12_macro_native_memory_seam_gate_v1b.sh ~/workspace/spk-evidence/spk-v5-t12-macro-native-memory-seam.json
```

The presence of the five original memory APIs and at least one successful original memory admission must still be checked on fwork. The partial local checkout cannot demonstrate that requirement.
