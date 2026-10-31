# SPK S3.7d/3b2b2k/15: Owned Root Emission Frontier v0

## Scope

Read-only, **conditional** source-emission prefix evidence for nodes with **no incoming Network v0 edges**, within a **single-owner, finite, sealed external-ingress epoch**. This module does not infer watermarks from idle service time, and accepts neither caller-issued `SOURCE_EMISSION` claims nor artificial confirmations.

## Conditional guarantee

For a root neuron N and logical time T, `SOURCE_PREFIX_CERTIFIED` establishes:

> No **new** Core emission with `EVENT_TIME <= T` can arise from N, conditional on the sealed finite input contract and the authenticated single-owner service/commit snapshot.

The guarantee concerns generation of **new** output, not eventual **delivery** of outputs that already exist. The certificate is **not** a `BATCH_CONSUME` authorization. Network v0 is event-driven; a neuron without input events does not spontaneously run Core batches.

### Preconditions checked

1. Immutable `SealedExternalIngressEpochV0` matches the boundary-owned ingress ledger, architectural profile, epoch and exact network nodes.
2. Exact physical external-event accounting is re-derived with `analyze_owned_external_prefix_v0`, which validates occupancy and service-time release constraints.
3. For N, no topological inbound edge exists and no routing manifest occurrence pretends to target N.
4. Every sealed input index with target N and `EVENT_TIME <= T` was *consumed*, not merely admitted to EVENT.
5. The complete existing Core commit history is replay-audited using `audit_committed_internal_history_v0` with architectural output context: P/S read evidence, state versions, Core transition recomputation, service confirmation and atomic publication when applicable.
6. Every declared historical batch of N at or before T has a matching commit. Its authenticated witnessed EVENT input indices exactly partition the sealed external prefix; mismatches, missing witness, duplicates or unrelated routed identities block the certificate.

### Statuses

- `SOURCE_PREFIX_CERTIFIED`: all above checks hold for the root/time pair.
- `INBOUND_EDGES_UNPROVEN`: source is not a root; a later inductive component is required.
- `INCONSISTENT_ROUTE_MANIFEST`: manifest purports an inbound route to a root.
- `EXTERNAL_PREFIX_PENDING`: sealed input at or before T is not accounted in the owned boundary.
- `EXTERNAL_EVENTS_UNCONSUMED`: known external input is resident but lacks consumption.
- `ROOT_BATCH_COMMIT_PENDING`: some declared root batch has not committed.
- `ROOT_INPUT_COMMIT_MISMATCH`: input identities and authenticated committed Core witnesses do not cover one another exactly.

Malformed identities, versions, histories, epochs, graph dependencies and illegally constructed storage states are rejected rather than certified.

### Critical limitations

- Only **in-degree zero** nodes; no recursive frontier propagation through inbound routes. This is a sound base case for later induction over strictly positive edge delays.
- Does not certify an open/live input stream: the finite epoch seal is an **explicit assumption**, not proof that the physical world has finished sending events.
- Snapshot ownership is an architectural trust boundary. Dataclass immutability is not cryptographic authenticity or persistent anti-rollback protection.
- Does not bind newly generated dynamic `STAGED` service requests into a shared runnable scheduler, create destination batches, grant EVENT slots or close a destination batch.
- A source prefix certificate says there will be no *new* emission at or before T. Existing emissions still in OUTPUT, EVENT, or STAGED must be independently accounted before downstream closure.
- No deadlock classification, no timeout-based completion, no change to frozen Core/Network/Compiler v0.

## Next milestone

Combine these **root** emission certificates with authenticated finite external prefixes and already registered routed occurrences. Progressively prove non-root frontiers via causal induction over strictly positive Network v0 edge delays, accounting for all outstanding delivery and commit work. A general dynamic `BATCH_CONSUME` must still wait until all upstream and external prefixes, physical event residence and service authorization are jointly satisfied.
