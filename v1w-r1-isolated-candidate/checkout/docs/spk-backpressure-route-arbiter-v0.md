# SPK S3.7d/3a: Bounded Route Backpressure Arbiter v0

Status: **candidate**, additive simulator primitive; not frozen.
Frozen Core v0, Network v0 and Compiler v0 are unchanged.

## Goal

A deterministic, single-owner arbitration boundary for routing requests that
already have one provenance-bound spike retained in their source `output_slots`.
The arbiter uses S3.7d/1's actual finite `event_slots` reservation ledger,
including external residents, routed residents, and reservations already held.

`arbitrate_routed_reservations_v0(architecture, manifest, storage, ledger,
state, *, service_boundary, newly_ready_route_ids=())`
returns an immutable `BackpressureArbitrationResultV0`:

- `granted_route_ids`: successful new destination reservations;
- `denied`: capacity denials including route ID, target PE, claimed/capacity,
  and explicit SERVICE_TIME boundary;
- `ledger`: new finite reservation snapshot;
- `state`: updated strictly-increasing boundary and waiting-route IDs.

Waiting IDs are **diagnostic/control metadata**, not additional storage for
spike payloads. Every denied spike must remain physically accounted for in
`storage.pending_output` at its source PE. No implicit unbounded packet queue.
The function leaves `storage` unchanged and cannot silently deliver events.

## Arbitration and progression

- The caller supplies the set of newly ready ROUTE_ENQUEUE requests once.
  It must prove causal readiness and supply a valid upstream routing binding.
- At a SERVICE_TIME boundary: older blocked routes are considered first in
  original FIFO retry order; simultaneous new requests are sorted by route ID.
- Each attempt calls the existing `reserve_routed_event_slot_v0`. A denied
  claim leaves the ledger unchanged for that route and records its ID as waiting.
  Further available capacity on other destinations remains usable.
- The caller may invoke a **later** SERVICE_TIME boundary after explicitly
  applying already validated consume/commit/external transitions to storage and
  ledger. Waiting routes are retried without being resubmitted as new.
- Equal or reversed boundary calls, missing source outputs, already reserved
  routes, reused/unknown IDs, mixed epochs, or invalid snapshots are rejected.
- Existing `output_slots` are finite; source output production that exceeds
  capacity fails at its own earlier transition, not here.

The result contains only new grants: the caller retains control of earlier
reserved routes and may later commit them using S3.7d/1. There is no
preemption, timeout, hidden cancellation, implicit ingress buffering, or
implicit event-time conversion.

## Crucial scheduling boundaries

The arbiter is **not yet a scheduler**. It does not generate service slices,
change the completion of a ROUTE_ENQUEUE request, prevent premature BATCH_CONSUME
or delay the production of new spikes when output fills. A route is eligible
only after causal output creation, under the same explicit SERVICE_TIME
contract as S3.7d/2. External events must be admitted before arbitration at
any equal boundary under the declared priority rule.

A blocked request is not necessarily a deadlock. Progress or feasibility
cannot be inferred from an isolated snapshot. Cyclic waits, quiescence,
priority starvation, bounded service execution, and external ingress
non-backpressurability require a future scheduler-level protocol. One state
owner serializes concurrent proposals: this is not a physical multi-writer lock
or distributed mutual exclusion guarantee.

## Test acceptance

- Competing routes on a one-slot PE: one grant, one explicitly blocked;
- no event loss, duplication or phantom slot claims;
- retry fails while capacity remains occupied and succeeds after consumption;
- older blocked request wins over newly presented work;
- route to independent PE advances despite another PE being full;
- external resident and existing routed resident block reservations;
- determinism across new request order, parallel identity preservation;
- wrong epoch, stale output, invalid ID and temporal reversals fail closed;
- no changes to Core, Network, Compiler or prior simulator APIs.

After validation, S3.7d/3b will integrate this with an independent causal
scheduler loop, explicit blocked-request state, progress/deadlock detection,
max-service-tick bounds, and verification against the existing service gate.
