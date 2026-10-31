# SPK S3.7d/3b2b2k/20: Owned Shared EVENT Cycle v0

## Status and dependencies

Candidate integration. Adds a **new** immutable composite owner without changing
SPK Core v0, Network v0, Compiler v0 or the already-validated route modules.
This is a restricted mixed EVENT cycle, **not** the complete autonomous scheduler
or an authenticated global Boundary Controller.

Depends on:

- `OwnedDynamicRouteServiceCycleStateV0` and its routed-only service contract.
- `OwnedDynamicRouteTransitStateV0`, `advance_owned_dynamic_route_transit_v0`.
- `advance_service_quantum_v0`, for finite routed service.
- `SealedExternalIngressEpochV0` and `seal_finite_external_ingress_v0` for a
  **closed, finite** input set declared at epoch initialization.

The composite state stores dynamic routed transit/service/reservations alongside
resident external-input indices. Both kinds of occupancy are charged against
**one per-PE `EVENT` physical capacity**.

## Invariants

For each PE `p`, in every accepted composite state:

```
external_resident[p] + routed_EVENT_resident[p] + routed_EVENT_reserved[p]
    <= architecture.pes[p].event_slots
```

The two types of identity remain separate:

- `input_index`: occurrence in the **sealed external plan**;
- `event_id = route_request_id`: computed routed occurrence and service request.

Indices may have equal numeric values without colliding. EVENT_TIME does not
advance because SERVICE_TIME advances. No route grant is inferred from mere
SOURCE OUTPUT residency if physical capacity is unavailable.

### One boundary (`advance_owned_shared_event_cycle_v0`)

1. Validate the immutable composite state and all capacity claims.
2. Admit **every** sealed external input whose `arrival_boundary` equals the
   current `ServiceQuantumStateV0.next_service_tick`. External ingress is
   non-backpressurable. Failure raises `SharedExternalIngressOverflowV0` with
   boundary, index, PE, occupied and capacity, returning **no new state**.
3. Reserve any remaining EVENT space for computed pending OUTPUT routes whose
   source emission is already confirmed, in ascending route/request ID order.
   Existing partial work retains its reservation.
4. Advance one finite PE quantum, rejecting all non-ROUTE_ENQUEUE slices.
5. Physically transfer service-finished routes OUTPUT → EVENT and confirm the
   ROUTE_ENQUEUE only after delivery; retire those reservations.
6. Return one new immutable shared state, its PE usage and the exact transition
   report. No operation silently consumes an external input or a route.

External inputs are admitted **before** NEW route grants at the same boundary;
prior route claims are not evicted. If a new external occurrence is due at a
later boundary already occupied by a persistent route reservation, the owner
raises an explicit `EXTERNAL_INGRESS_OVERFLOW`. The future general scheduler
will need admission look-ahead or a capacity policy for this condition; this
restricted module does not fabricate a buffer or cancel already-served work.

## Limited capabilities and explicit non-goals

- The composite owner does **not** yet consume external EVENT inputs, because
  BATCH_CONSUME requires a separately authenticated batch-closure authority.
  Consequently external slots persist and a long run can remain backpressured.
- It does **not** publish a Core source emission, admit terminals, allocate new
  dynamic requests, authorize destination batches or detect deadlock.
- It does **not** replace the existing `BackpressureBoundaryController` and does
  not yet reconcile its `EventReservationStateV0`. It *demonstrates a correct
  shared slot budget in one incremental owner* using the earlier route lane.
  Integrating the global controller and consumption ledger remains required.
- An initial caller-constructed service/storage history and the input seal are
  still trust roots. The constructor verifies their *internal consistency*, not
  their historical authenticity or protection against snapshot forks.
- Existing external inputs with `arrival_boundary < next_service_tick` must
  still be in the composite resident set: this version has no external consume.
  The restricted owner is suitable only for a consistent closed-plan starting
  snapshot, typically one initialized before its earliest admitted ingress.
- External batch-release `consume_request_id` binding and destination consumer
  generation are out of scope. No `BATCH_CONSUME` may be asserted from this
  module's positive status.
- `WAITING` and backpressure **never** mean deadlock.

## Acceptance criteria, S3.7d/3b2b2k/20

1. One shared finite EVENT capacity for both classes of occurrence on each PE.
2. Mandatory exact-SERVICE_TIME sealed external arrivals, no silent delays.
3. No routing grant in excess of capacity after external admissions.
4. Multi-cycle route reservations, physical delivery and correct confirmation.
5. Explicit overflow with immutable input on impossible external admission.
6. Separate identity namespaces and preserved EVENT_TIME and multiplicity.
7. Snapshot determinism, rejection of absent/premature/duplicate external indices.
8. Legacy suite remains green and frozen Core/Network/Compiler remain unchanged.

Expected new test count: 43. Expected full project count, assuming previous
2,138 tests: **2,181**. As always, these counts are expectations until the
suite is run on fwork with its actual module contracts.

## Next integration

The next required integration must connect externally consumed and routed EVENT
occurrences to **one authentic destination-batch consumption owner**, then
reconcile that state with the already existing external
`EventReservationStateV0`/Boundary Controller. A separate closure proof is
required before any storage slot may be released by `BATCH_CONSUME`.
