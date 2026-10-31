# SPK S3.7d/3b2b2k/21 · Owned Sealed Root Batch v0

## Scope

A **read-only, trust-conditional completeness proof** for the sealed external
inputs of a **root neuron** (a neuron with no incoming edges in frozen
Network v0). This provides the first explicit dynamic batch-input certificate
on the **same snapshot** as the Shared EVENT capacity owner.

No functional replay trace is consulted. `EVENT_TIME` and `SERVICE_TIME`
remain distinct. The input seal must be installed immutably by the future
single-owner epoch initializer. A caller can forge the initial snapshot;
this module does not authenticate arbitrary prior histories.

## API

```python
analyze_owned_sealed_root_batches_v0(
    state: OwnedSharedEventCycleStateV0,
) -> SealedRootBatchAnalysisV0
```

Every `SealedRootBatchCandidateV0` reports exact external input indices
including duplicates on the same target channel, the PE, `EVENT_TIME`,
`BATCH_CONSUME` request ID, resident/pending indices, a status and
`sealed_input_set_complete`.

## Preconditions for `ROOT_INPUT_SET_READY`

1. The externally declared epoch input plan is finite and sealed, and is
   consistent with the immutable Shared EVENT snapshot.
2. The destination neuron has **zero incoming topology edges**: no network
   spike can reach it at any `EVENT_TIME`.
3. All sealed input occurrences for precisely this `(node, EVENT_TIME)` have
   been admitted by their actual SERVICE_TIME and remain physically resident.
4. The corresponding static `BATCH_CONSUME` request has matching ID, node,
   domain EVENT, PE, epoch, `EVENT_TIME`, and **quantity**.
5. The candidate is at the **earliest** external event time for that node.
   The present Shared EVENT owner cannot yet consume external occurrences;
   later batches must not skip an earlier one.
6. Only one consume request ID may denote the batch at a particular
   `(node, EVENT_TIME)`. Ambiguous groupings are rejected.

An external input planned for the same `EVENT_TIME` but a later SERVICE_TIME
remains pending; mere service-clock advancement or quiet buffers never closes
that input set.

## Fail-closed behavior

- `SEALED_INPUTS_PENDING`: at least one expected occurrence is absent.
- `NONROOT_REQUIRES_CAUSAL_FRONTIER`: incoming network edges could still
  deliver additional events. Even a physically resident external batch is
  *not* sufficient for a nonroot neuron.
- `EARLIER_ROOT_BATCH_UNCONSUMED`: a later root batch is not ready while a
  previous logical-time batch is still resident.
- Malformed request/epoch/quantity/PE/grouping: explicit `ValueError`, no
  silent adjustment and no fabricated request identity.

## Explicit NON-guarantees

- `sealed_input_set_complete` is **NOT** authorization to start
  `BATCH_CONSUME` service: program/state/dependency service and service
  admission remain external, separately verified obligations.
- It does **NOT** consume events, free EVENT slots, update neuronal state,
  confirm service, or record Core outputs.
- It does **NOT** certify a nonroot batch or an open/live ingress stream.
- It does **NOT** prove the historical authenticity of a caller-constructed
  snapshot. The future single-owner epoch runner must own initialization.
- `supports_consume_confirmation` is always `False`.

## Tests

32 targeted tests exercise actual Shared EVENT admissions, delayed inputs,
root/nonroot separation, multiplicity, exact quantity/epoch/time binding,
no double consumption, input presence, snapshot invariance and failure modes.

The reconstructed local SPK integration lab reports **1,063 passed** with
some substituted architecture/Compiler interfaces. The real fwork repository
must run `python -m pytest -q`; expected count after S3.7d/3b2b2k/20 is
**2,213** (2,181 previous + 32 new). This number is a target, not a claim of
successful execution on fwork.

## Next

Bind the root input-set proof to a real `BATCH_CONSUME` service grant and
its eventual authenticated consumption, with an **atomic update of shared
EVENT occupancy and the consumed-input ledger**. A later release must then
extend the causal frontier proof to nonroot batch formation, generated routes,
and a single owner for the whole network.
