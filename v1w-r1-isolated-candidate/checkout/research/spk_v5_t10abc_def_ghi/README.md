# SPK V5 · T10ABC/DEF/GHI cumulative provider gate

Three grouped research deliverables:

- **T10ABC**: a separate provider authorizes the actual `SEM_B_C` tick's P write via a SQLite UDF called by a store-side SQL trigger, retaining the inherited T9 fence.
- **T10DEF**: 96-episode comparisons for control, serial, three in flight, affinity and per-wave restart; eight valid provider authorizations in trained scenarios with exact T9 functional parity.
- **T10GHI**: provider denial rolls back the same atomic C tick and leaves its receipt queued for recovery; concurrent same-version verdicts get one grant; direct writes/alteration are rejected; native admission remains unavailable.

This only implements a host-controlled **reference provider**, NOT original SPK Memory Contract, native BV or native learning. Host forgery remains possible. Frozen modules untouched. See `docs/spk-v1-reference-provider-native-adoption-boundary.md`.

After `tar --skip-old-files` extraction run `bash search/spk_v5_t10abc_def_ghi_cumulative_gate.sh ~/workspace/spk-evidence/spk-v5-t10abc-def-ghi-cumulative.json`.
