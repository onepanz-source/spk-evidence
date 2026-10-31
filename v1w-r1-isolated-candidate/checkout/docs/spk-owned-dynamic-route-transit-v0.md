# SPK S3.7d/3b2b2k/18: Owned Dynamic Route Transit v0

## Purpose

Executable, capacity-bounded `OUTPUT -> EVENT` transition for dynamically
registered `ROUTE_ENQUEUE` requests, whose physical occurrence identity equals
the request ID. It is a **dynamic-lane integration prototype** and is NOT a
completed global simulator scheduler.

For every step, the module reconciles one immutable snapshot containing:

- `OwnedDynamicServiceRegistrationStateV0`: Core-derived identities,
  `EMISSION_RECORD` and `ROUTE_ENQUEUE` service requests and causal graph.
- `RoutedStorageStateV0`: actual pending `OUTPUT`, admitted `EVENT`, consumed
  occurrence tombstones, plus finite PE capacities.
- `ServiceQuantumStateV0`: incomplete, work-finished, confirmed service
  requests (not yet proof of where this initial snapshot came from).

It then selects registered routes in ascending request-ID order where:

1. The physical occurrence is in `OUTPUT`, with matching, audited provenance.
2. The source's dynamic `EMISSION_RECORD` is confirmed in service state.
3. The route's own `ROUTE_ENQUEUE` service is work-finished at or before the
   current `SERVICE_TIME` boundary.
4. The destination PE has an available `EVENT` slot.

For each eligible route it calls the existing immutable
`admit_routed_event_v0()` operation and **only after successful transfer**
replaces its `ServiceFinishedV0` with `ServiceConfirmedV0` in the same returned
snapshot. Full storage/capacity and identity reconciliation is repeated on the
successor snapshot. There are no externally supplied “completed IDs” or
proposed route selections.

## Key invariants

- Every routed occurrence is still identified by its allocated
  `ROUTE_ENQUEUE` request ID.
- Dynamic source fan-out must be all published or all unmaterialized;
  a partly materialized emission is rejected even if other routes have since
  advanced from `OUTPUT` to `EVENT` or `CONSUMED`.
- `STAGED` routes cannot have ongoing/completed route service. An `OUTPUT`
  route cannot already be service-confirmed. An `EVENT`/`CONSUMED` route must
  have its own confirmed route service.
- The source's `EMISSION_RECORD` must be confirmed before any dynamic
  occurrence is physically materialized. Graph predecessors of all in-flight
  and confirmed requests must themselves be confirmed.
- If `EVENT` is full, the route remains `OUTPUT` and awaiting confirmation;
  the transition reports `BACKPRESSURE` without advancing `SERVICE_TIME`.
  Other independent routes may advance if capacity permits.
- `EVENT_TIME` is never rewritten or inferred from `SERVICE_TIME`.
- Batch-closure flags and `BATCH_CONSUME` remain **disabled**.

## Boundaries NOT established by this component

**IMPORTANT**: The input `OwnedDynamicRouteTransitStateV0` can be constructed
by a caller. Its service and storage histories are strongly reconciled, but
are **not cryptographically or independently authenticated**. Only a future
single-owner scheduler, which constructs and retains the complete joint
snapshot from actual earlier transitions, can close that trust boundary.

This component also does **not** perform:

- The prior Core `STATE_COMMIT`/full-fanout `OUTPUT` publication;
- An initial memory grant or the consumption of route service units;
- Coordination with the existing static Backpressure Boundary Controller's
  grants, reservations or ingress ledger;
- `BATCH_CONSUME` or a destination Core transition;
- Full dynamic source-frontier proof / completion or general deadlock proof.

Do not substitute its output for the existing controller's complete
`AuthenticatedServiceBoundaryStateV0` in a real unified execution.

## Acceptance

- 33 focused tests, including two dynamically registered routes, successful
  transfer, finite `EVENT` backpressure/retry, disallowed premature completion,
  stale/mismatched provenance, and immutable snapshots.
- Regression gate: full SPK suite on the user's real repository.
- Freeze only after independent verification. Core/Network/Compiler v0 remain
  unchanged.

## Next work

Move the registration ledger and this transport step inside the actual
Backpressure/Service controller's single owner: connect dynamic source
publication, route service starts/grants, finite-event transfer and eventual
batch closure. The current prototype intentionally does not bypass any of
those missing permissions by declaring the network autonomous.
