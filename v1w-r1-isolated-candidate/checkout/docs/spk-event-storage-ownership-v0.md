# SPK Routed Event Storage Ownership v0

Status: DRAFT, S3.7a executable storage-state model
Baseline: frozen Core v0 + Network v0
Parent: `docs/spk-backpressure-contract-v0.md`

## Scope

Pure transitions for **routed** spike occurrences. This is **not** operational
backpressure, dynamic scheduling, authentication, or physical memory simulation.
Existing `ProcessingElementV0.output_slots` and `event_slots` supply separate
finite capacities per PE. One routed occurrence occupies exactly one slot.
No implicit unbounded in-transit queue is available in this v0 model.

## Lifecycle and ownership

- A newly proposed routed occurrence is **not successfully produced** until
  `offer_routed_output_v0` has reserved a source `OUTPUT` slot.
- `PENDING_OUTPUT`: source PE owns and retains the event occurrence.
- `ADMITTED_EVENT`: `admit_routed_event_v0` atomically moves ownership to one
  destination event slot. If that slot is full, the event **remains pending**.
- `CONSUMED`: `consume_routed_event_v0` frees the destination slot, recording
  the event ID as host-side reconciliation metadata.

For each accepted event ID, there is exactly one of these three states.
The event may not be stored simultaneously in both source and destination.
A failed transition never mutates input state or claims successful delivery.

## Identity and time

Every routed spike has a unique, nonnegative integer `event_id` within an
execution epoch, independent of payload equality. Event IDs may ultimately
be linked to `ROUTE_ENQUEUE` request IDs from S3.3. This binding is **not**
yet implemented. `emission_event_time` and `delivery_event_time` are retained
unchanged; only strictly positive logical routing delay is accepted.
No SERVICE_TIME is created or inferred by these transitions.

## Capacity and failure

- `OUTPUT` capacity is checked before accepting a new routed occurrence.
- `EVENT` capacity is checked before atomic transfer.
- `RoutedStorageBlockedV0` reports the blocked PE, domain, occupancy and cap.
- No event is silently lost, duplicated, admitted over capacity, or reused
  under an already consumed ID.
- A blocked **offer** means the neuron/router has not yet successfully
  materialized the new routed event. The producer must be stalled by a
  future controller or the run rejected; the code does not stall it itself.

## Accounting and limits

`RoutedStorageStateV0` is an immutable replay state. Its `consumed_ids`
contains **host-side diagnostic tombstones**, not physical event slots. This
metadata is not a license for unbounded live architecture memory; a future
retention/epoch contract must limit or retire it.

External ingress buffers and transient interconnect storage are outside
this model. Source/destination node placement, routing edge validity, and
BATCH_CONSUME authorization must be bound to Network v0 and A2 separately.
A proposed event's fields are not trusted by themselves. In particular,
`offer_routed_output_v0` does not verify an actual Core emission.

This state model is single-step and atomic **at the abstract model level**.
It does not model concurrent reservation races or guarantee deadlock freedom.

## Next acceptance gate

Bind unique routed-event identities to observed routing/provenance, account
for external arrivals, then implement a capacity-aware causal controller.
Only then is active backpressure eligible for conformance tests BP01-BP12.
