# SPK Backpressure Contract v0

Status: DRAFT
Baseline: spk-core-network-v0
Parent: spk-memory-contract-v0.md

## 1. Purpose

Define the conditions under which event delivery may
be suspended because architectural storage is full.

Backpressure must not silently modify the functional
SPK Core or Network semantics.

## 2. Fundamental invariants

- No silent event loss.
- No event duplication.
- No implicit event deduplication.
- No modification of EVENT_TIME.
- No completion of an enqueue without accounting
  for the destination event slot.
- No implicit unlimited pending-event storage.

## 3. Storage ownership

Every pending event occurrence must have an explicit
storage owner.

Potential storage locations include:
- source output buffer;
- interconnect transit buffer;
- destination event buffer;
- external ingress buffer.

Each implemented storage location must have an
explicit finite capacity.

The current Event Buffer Audit covers only
destination PE event-slot occupancy.

Other storage locations are not yet implemented.

## 4. Event lifecycle

An event occurrence must have a uniquely traceable
identity across the architectural lifecycle.

Proposed lifecycle:

CREATED
PENDING
ADMITTED
CONSUMED

A rejected workload is not a successful execution.

Lifecycle transitions must preserve multiplicity.

## 5. Backpressure condition

A destination may admit an event only when sufficient
capacity is available or reserved.

If admission is impossible, the producer must
either:

- retain the event in explicitly accounted storage;
- wait under a declared flow-control protocol;
- or fail explicitly.

A producer must not continue as though delivery
had completed.

## 6. External ingress

An external arrival boundary denotes event
availability, not an unlimited storage guarantee.

External sources are backpressurable only if an
explicit handshake protocol permits suspension.

Otherwise sufficient ingress capacity must be
reserved or the workload rejected explicitly.

## 7. Atomicity

Event admission and slot accounting must be
consistent.

Concurrent producers must not reserve the same
free slot independently.

Reservation and delivery semantics require
a future executable contract.

## 8. Temporal semantics

SERVICE_TIME may increase under backpressure.

EVENT_TIME remains unchanged.

Any architectural schedule that cannot preserve
the frozen functional event ordering must be
reported as infeasible rather than silently
changing the neuronal computation.

## 9. Deadlock and progress

Backpressure may introduce wait cycles across PEs.

The simulator must distinguish:
- waiting for a future external arrival;
- waiting for service capacity;
- waiting for buffer capacity;
- deadlock without possible progress.

Finite execution limits remain mandatory.

Priority alone does not guarantee progress.

## 10. Initial implementation boundary

The first implementation should support
fail-closed detection of insufficient capacity.

Active producer suspension requires:
- bounded pending-event storage;
- event ownership;
- explicit reservation;
- delivery completion rules;
- deadlock detection.

No active backpressure behavior is authorized
by this DRAFT contract alone.

## 11. Acceptance candidates

BP01 - No silent event loss
BP02 - Duplicate spike preservation
BP03 - No admission beyond buffer capacity
BP04 - Reservation uniqueness
BP05 - Producer suspension retains event ownership
BP06 - External non-backpressurable ingress rejection
BP07 - Independent PE progress
BP08 - Cross-PE congestion propagation
BP09 - Deadlock detection
BP10 - SERVICE_TIME delay without EVENT_TIME mutation
BP11 - Functional Network v0 equivalence
BP12 - Deterministic replay
