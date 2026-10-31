# SPK S3.7c/1 - Causal Routed Ownership Replay v0

Status: **DRAFT, post-hoc audit, not operational backpressure**.

Input: frozen architecture profile; S3.7b routed binding built from real
Network v0 observations; logical access plan; mapped service requests;
completed S3.5/S3.6b causal service schedule.

Each routed occurrence follows exactly three SERVICE_TIME transitions:

1. **OFFER** at completion of its source `EMISSION_RECORD` request.
   The source PE owns an `OUTPUT` slot.
2. **ADMIT** at completion of its `ROUTE_ENQUEUE` request.
   Ownership transfers atomically from source `OUTPUT` to destination `EVENT`.
3. **CONSUME** at completion of the bound destination `BATCH_CONSUME`.
   The destination slot is released. Its identity remains only in diagnostic
   reconciliation metadata.

The replay requires `offer_tick < admit_tick < consume_tick` for each route.
At equal boundaries for unrelated routes, completed consumptions are applied
before admissions, and admissions before offers. This is a declared v0
boundary convention, not proof of subcycle ordering in physical hardware.

All route identities, epoch, source/destination node, PE and logical timestamps
come from the binding. The replay validates request/reference/completion coverage
and per-request service-unit conservation. Parallel-edge occurrences retain
separate request IDs and independent slots; their `EVENT_TIME` is untouched.

The replay uses existing S3.7a finite output/event capacities. On insufficient
capacity, the immutable input state and frozen schedule are not rewritten;
`RoutedStorageBlockedV0` is raised. **This is rejection, not producer stalling.**

## Important boundary

- Routed event occupancy is a **lower bound** on total destination EVENT
  occupancy. External spikes can occupy the same physical event slots.
  A successful S3.7c/1 replay **does not prove EVENT capacity** for mixed
  external and routed workloads: run the existing full
  `audit_event_buffers_v0(..., ingress=...)` independently.
- An `EMISSION_RECORD` is a completed service request in a precomputed
  functional trace; no instruction is executed live.
- Service-time ownership and the old scheduler are inspected **after the
  fact**. No backpressure, rescheduling, reservation protocol, producer stalls,
  transit buffer, deadlock detection or interconnect modeling is implemented.
- Historical diagnostic `consumed_ids` is host metadata; it does not represent
  unbounded physical buffer capacity.
- The signature of existing Core, Network, Compiler v0 and existing scheduler
  remains unchanged.

## Acceptance criterion

Unique bounded event ownership; exact route-to-consumer reconciliation;
causal completion ordering; service conservation; deterministic identical replay;
explicit error on source `OUTPUT` exhaustion and destination routed `EVENT`
exhaustion; no event loss, duplication or silent deduplication.
