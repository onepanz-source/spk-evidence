# SPK S3.7d/1: Event Slot Reservation v0

Status: candidate, not frozen. Additive simulator component only.
Baseline contracts: `spk-core-network-v0` and `spk-compiler-v0` unchanged.

## Purpose

Before a routed spike moves from the producer output buffer to the consumer
PE event buffer, grant a unique finite slot claim. A slot claim does **not**
complete `ROUTE_ENQUEUE` or change the event's `EVENT_TIME`.

This component is a **deterministic, single-state-owner functional model**.
It does not perform live service scheduling, concurrent CAS/locks, hardware
atomic operations, deadlock detection, or backpressure propagation.

## Inputs and trust boundary

* `ArchitectureProfileV0` defines real PE `event_slots` and `output_slots`.
* `RoutedBindingManifestV0` must originate from the validated observed
  Network v0 routing trace (`bind_network_routes_v0`).
* `RoutedStorageStateV0` models individually owned routed occurrences.
* `ExternalIngressBindingV0` must originate from `bind_external_ingress_v0`
  with the **complete** initial-event sequence and validated provenance.

The reservation module validates internal identity, profile, epoch, and
capacity consistency, but does **not** rerun the upstream functional trace
or attest that a caller-provided binding is authentic. A caller must not
replace the ingress binding partway through an epoch.

## Invariants

For each PE, at every admitted transition:

```
external_resident + routed_admitted + reserved_routes <= event_slots
pending_output <= output_slots
```

A pending route keeps its **source output slot** even after successful
reservation. `commit_routed_event_slot_v0()` performs a pure, paired update:
release the source output slot, occupy the destination event slot, and
remove **exactly one** reservation. Its input states are never mutated.
An invalid request raises an explicit exception with no new accepted state.

Reservations are identified by ROUTE_ENQUEUE request IDs bound to Network v0
occurrences. Parallel edges and equal-timestamp spikes remain distinct.
External occurrences are separately identified by input indices and share
`event_slots` with routed spikes.

`cancel_routed_event_slot_v0()` releases only the claim; it does not discard
or implicitly deliver the spike. Repeated reservation, arrival, consumption,
and transfer without reservation are rejected. Epoch isolation is strict.

## Operations

* `event_reservation_usage_v0`: inspect the capacity ledger.
* `reserve_routed_event_slot_v0`: claim a destination event slot while
  retaining the routed spike in source output.
* `cancel_routed_event_slot_v0`: release an unused claim; source still owns it.
* `commit_routed_event_slot_v0`: simultaneously turn one reservation into
  resident destination occupancy and complete the source transfer.
* `arrive_external_event_slot_v0`: record an external occurrence as resident;
  fail explicitly if event capacity is unavailable.
* `consume_external_event_slot_v0`: release a resident external occurrence,
  strictly matching its consuming batch request.
* `consume_reserved_routed_event_v0`: release an already delivered routed
  occurrence using the provenance-bound consumption request.

All operations are **logical state transitions**, not PE service transactions.

## Explicit limitations

1. **No clock enforcement:** the caller must enforce `arrival_boundary` and
   causal SERVICE_TIME completion using the release-aware scheduler. No
   derivation from `EVENT_TIME` is allowed.
2. **No external holding buffer:** an external arrival rejected for lack of
   capacity makes the input sequence infeasible unless an explicit upstream
   backpressure/ingress protocol exists; the event has not been stored.
3. **No parallel writes:** the state owner must serialize updates to the
   immutable ledger. Two independent threads applying transitions to the
   same older snapshot can overbook without an external transaction protocol.
4. **No active producer suspension:** a denied reservation leaves the routed
   occurrence in the source output buffer, but the scheduler does not yet
   wait/retry or avoid deadlocks.
5. Consumed-ID tombstones remain reconciliation metadata in host memory,
   not an infinite architectural storage allowance. Epoch retention must
   eventually be specified.
6. Successful reservation does not establish that a complete workload is
   physically feasible. Existing complete buffer audits and functional
   trace equivalence gates remain required.

## Next: S3.7d/2

Integrate reservation transitions with service completion boundaries. Enforce
one serialized owner for each reservation ledger, distinguish a blocked route
from a non-backpressurable external arrival, and add bounded wait/progress
conditions. Do not modify the frozen compiler or the functional Network.
