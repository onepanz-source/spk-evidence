# SPK S3.7d/2: Service-Time Event Reservation Gate v0

Status: candidate, not frozen. Additive simulator diagnostic only.
Core v0, Network v0 and Compiler v0 remain frozen and unchanged.

## Purpose

Bridge the existing finite occurrence reservation ledger (S3.7d/1) to the
completed causal scheduler's SERVICE_TIME trace. A route reserves a destination
`event_slots` claim at the **first service slice** of its `ROUTE_ENQUEUE`; it
commits that claim at service completion. The source event remains in its
`output_slots` until commitment. External occurrences share destination event
capacity with reserved and already-admitted routes.

**This is a post-hoc admission gate for an existing service schedule.** It is
not a live scheduler, real concurrent synchronization, hardware locking,
dynamic retry protocol, external ingress queue or deadlock detector.

## Entrypoint

```python
gate_service_reservations_v0(
    architecture, routing_manifest, logical_plan,
    service_requests, causal_schedule, bound_external_ingress,
) -> ServiceReservationGateResultV0
```

The caller must use a validated frozen Network routing witness,
`bind_external_ingress_v0` over the **complete** initial-event tuple, and an
existing release-aware causal schedule. The gate checks internally consistent
external batch releases, timing, service work and routed ownership, but it does
not re-execute Network v0 to authenticate caller-provided bindings. It cannot
prove all external occurrences were provided without upstream provenance.

## Boundary semantics

At a common SERVICE_TIME boundary, operations occur in this deterministic order:

1. Consume resident routed and external occurrences whose `BATCH_CONSUME`
   service completes at that boundary; free their slots.
2. Commit completed `ROUTE_ENQUEUE` transactions; replace each held reservation
   with actual destination residency, releasing the source output slot.
3. Admit external occurrences with exactly this declared arrival boundary.
   External ingress has priority over **new** reservations at an equal boundary.
4. Offer new routed occurrences when their `EMISSION_RECORD` completes.
5. Reserve an output-owned routed occurrence at the first `ROUTE_ENQUEUE`
   service slice, using available destination capacity.

A source output must exist when a reservation begins. An external batch may not
start `BATCH_CONSUME` service before its release boundary. Routed reservations
must begin no earlier than their `EMISSION_RECORD` completion and must start
strictly before their `ROUTE_ENQUEUE` completion. EVENT_TIME is untouched.

A reservation stays claimed over all service ticks from route start to route
completion. All routed/external event and output capacities derive from the
existing `ArchitectureProfileV0` (PE `event_slots` / `output_slots`).

## Denials, not silent loss

`ServiceReservationDeniedV0` makes infeasible capacity claims explicit:

- `ROUTE_RESERVATION_BLOCKED`: no free destination slot at route service start;
  the spike remains accounted for in the source output in the rejected trace.
- `EXTERNAL_INGRESS_OVERFLOW`: an externally arriving spike cannot be admitted
  at its availability boundary. No fictitious external buffer is inferred.

The exception records `code`, `service_boundary`, `occurrence_id`, `pe_id`,
`claimed`, and `capacity`.

A denial proves only that the **provided schedule** cannot satisfy this
conservative early-reservation rule. Another schedule or reservation policy may
be feasible. No schedule rewriting, retries or backpressure propagation occur.
All ledgers and storage snapshots are immutable; no partial result is accepted.

## Output and conservation

The result contains immutable ordered transitions, per-PE peak reserved/event
claims and output occupancy, and final storage / reservation state. Success
requires every route and every provided external occurrence to be consumed,
no pending routed output, no admitted routed events, no outstanding
reservations, and no resident external events.

The prior S3.7c/2 `OwnershipConsistencyAuditV0` remains independently necessary:
it checks final delivered and consumed event accounting against the complete
buffer audit. This gate focuses on **early capacity claims**, so successful
execution of one gate does not replace the other.

## Trust, concurrency, and remaining work

All ledger transitions are serialized under **one logical state owner** and
performed as pure snapshot transformations. This models atomicity in a
single-owner simulator only; concurrent PE writers, compare-and-swap,
transaction IDs, deadlock prevention, fair retries, finite external queues,
and upstream stalls remain unimplemented. The completed schedule is read-only.

Future S3.7d/3 should introduce an actual bounded wait/retry protocol, with
explicit ownership and causal progress/deadlock accounting. A positive outcome
from this gate is **not** proof of physically realizable live backpressure.

## Suggested acceptance

- One reservation per provenance-bound routed occurrence.
- Reservation before completed delivery; no reservation before output exists.
- No reuse of claimed event slots; external arrivals share the same slots.
- Explicit fail-closed route and external denial.
- Accurate per-PE peaks and empty final ledgers.
- No EVENT_TIME mutation; independent SERVICE_TIME boundary control.
- Existing S3.7d/1 and earlier tests remain passing.
