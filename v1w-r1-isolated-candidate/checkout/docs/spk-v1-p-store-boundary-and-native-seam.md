# SPK V5 T9STU/VWX/YZA: P-store boundary and native admission seam

Research-only checkpoint. No change to SPK frozen PE, BV-v0e, Architecture v1, Memory Contract, or prior V1 research modules.

## Why this is a real improvement

T8/T9 checks `P` authorization in the same Python function that processes the C-receipt event; callers capable of running a direct UPDATE against the research SQLite database could bypass the *normal* reference authorization path. The new subclass `FencedMultiTickEngine` adds a storage-side SQL trigger that admits an `UPDATE p` only when there is a consumed reference grant scoped to C, the same cue and version, and a completed `SEM_B_C` event with negative verdict. The trigger also requires the exact bounded state transition: flip 11/12, increment version once, decrement budget once. `INSERT` and `DELETE` are separately denied. This is a **reference-authority separation of concerns**, NOT a security boundary against a privileged host.

## Three grouped workstreams

- **T9STU, P-store enforcement**: preserve T9 scheduling and computational semantics, add the store-side fence; compare serial, batch3, context-affinity, control. All original 96-case core row digests must stay exactly identical to T9JKL.
- **T9VWX, target mapping and independent custody**: a second verifier reconstructs each granted C-receipt's A PE, A/B/C event and reference grant lineage. Map each grant to an exact `owner=C`, `domain=P`, `mode=execute`, `PE-C-RESEARCH`, `context`, `expected_version` target. `native_authorize` MUST fail closed with `NATIVE_MEMORY_CONTRACT_PORT_NOT_IMPLEMENTED`. No native SPK write or grant is made.
- **T9YZA, durability and negative tests**: reopening per admission wave retains all outcomes, lineage, and versions. Direct P mutation without a grant fails. Replays/stale receipts never gain authority. A privileged host is still capable of disabling the SQLite trigger or resealing a coherent database, which is explicitly outside the guarantee.

## Scope and acceptance

1. Preserve 84/96 at three free in-flight epochs, 88/96 by context affinity, 88/96 serially, 48/96 fixed control, with 32/48/96 waves respectively.
2. Maintain original T9 source core-row digests and eight **reference-v1** grants; preserve four stale vetoes in batch3 and zero in context-affinity.
3. Enforce `native_SPK_P_grants=0`, `native_SPK_P_writes=0`, and `native_learning=false` in the report and gate.
4. Verify 18 cumulative manifests, 12 original source pins, genuine BV-v0e preflight, all cumulative regression suites, two byte-identical independent reports.
5. Do not promote memory-target mapping to native Memory Contract admission without a new explicitly versioned native provider and test matrix. SHA-256 hashes and SQLite triggers do not authenticate a hostile privileged host.

## Next architecture task

Introduce a versioned native Memory Contract admission provider that receives a typed P target and evidence origin from the **native tick runtime**, and whose grant is applied by native P storage. Only thereafter can the reference grant interface be replaced, under side-by-side v0 frozen regressions, with a distinct versioned v1 adoption gate. If this provider is absent, fail closed rather than generating a fake native grant.
