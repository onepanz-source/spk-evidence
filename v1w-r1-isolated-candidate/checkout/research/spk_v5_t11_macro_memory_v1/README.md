# T11 macro · Executable Owned Memory V1 (new runtime, not frozen native)

Single additive macro milestone with six functional workstreams. It uses the
existing V1 research PE fragment/tick engine, applies a new versioned memory
authority during the actual C receipt UPDATE, records new-runtime grant lineage
atomically in a separate grant ledger, and fails closed in the absence of a
trusted original Memory Contract binding.

Main runtime: `memory_authority_v1.py`. Deterministic cumulative report:
`macro_gate.py`. Run full fwork gate:

`bash search/spk_v5_t11_macro_owned_memory_v1_cumulative_gate.sh ~/workspace/spk-evidence/spk-v5-t11-macro-owned-memory-v1.json`

Parent `fwork` evidence T10STU must exist and match expected SHA. Never copy this
reference into original SPK Memory Contract or claim native learning. See
`docs/spk-v1-macro-owned-memory-contract-integration.md`.
