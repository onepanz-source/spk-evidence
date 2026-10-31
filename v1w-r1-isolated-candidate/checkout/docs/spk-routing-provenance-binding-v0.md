# SPK Routing Provenance Binding v0

Status: DRAFT, S3.7b executable trace-to-storage binding
Baseline: frozen Core v0 + Network v0
Parents: `spk-backpressure-contract-v0.md`, `spk-event-storage-ownership-v0.md`

## Purpose

Tie each *routed spike occurrence* retained by the S3.7a storage state to a
specific `ROUTE_ENQUEUE` access from S3.2/S3.3 and a destination
`BATCH_CONSUME` batch. The binding is constructed from a completed Network v0
functional observation, validated logical access plan, and reconciled input
provenance. Caller-proposed route payloads are **not** sufficient evidence.

## Stable occurrence identity

- `RoutedOccurrenceV0.event_id = ROUTE_ENQUEUE.request_id`, scoped to `epoch_id`.
- Parallel edges yielding identical payloads still receive distinct route
  request IDs and must occupy distinct storage slots.
- Every bound route identifies its destination `BATCH_CONSUME.request_id` and
  observed batch index. One batch may consume several routed occurrences.
- Source/destination node, PE, channel, and both logical timestamps are derived
  from the matching observed route, not recomputed from service completion.
- Only positive logical edge delays are supported, as in frozen Network v0.

## Reconciliation requirements

`bind_network_routes_v0` re-runs `reconcile_event_provenance_v0` and refuses
mismatches in trace, logical plan, initial events or placement/profile. Each
routed request must correspond to one observed route and exactly one consuming
batch. Channel multiplicity is preserved. No physical delivery ordering is
inferred from the historical execution trace.

## Storage transitions

`offer_bound_routed_event_v0`, `admit_bound_routed_event_v0` and
`consume_bound_routed_event_v0` wrap S3.7a transitions. The offered event is
sourced **only** from the manifest. Every operation also checks that **all** resident routed events and consumed-ID
tombstones belong to the binding. Admission and consumption compare stored
occurrences with the binding; consumption also requires the matching logical
batch-consume request ID. Existing OUTPUT/EVENT capacities remain enforced.

These functions are **pure state transitions**. A failed transition leaves the
original immutable state unchanged. The binding does not assert that the
corresponding service transaction has completed. This is the future causal
controller's responsibility.

## Explicit limitations

- Binding an observed reference trace is consistency verification, **not**
  cryptographic authentication of an arbitrary host-language object.
- Direct S3.7a functions remain available for structural testing; this wrapper
  is the trace-grounded integration path, not an enforced security perimeter.
- No live event generation, backpressure suspension, dynamic reservation,
  interconnect transfer delay, or deadlock detection is implemented.
- External ingress is out of scope for these routed-event identities.
- Diagnostic consumed-ID tombstones still require a bounded retention policy.
- Completion of a routed enqueue and occupancy transfer are not yet coupled
  atomically to the service scheduler. Therefore **this is not yet a sound
  operational backpressure controller**.

## Acceptance gate

Validate distinct parallel-edge identities, trace-to-request and
request-to-consume coverage, node/PE/channel/epoch agreement, mismatched
observations and access plans, output/event capacity failures, and deterministic
replay. Do not modify frozen Core v0 or Network v0.
