# SPK External Ingress Availability v0

Status: DRAFT - S3.6b/1
Baseline: frozen Core v0 and Network v0

## Purpose

Represent when each **initial event occurrence** becomes available in
`SERVICE_TIME`, without deriving availability from its `EVENT_TIME`.

This is a finite availability plan. It is **not** a live-event-ingress
controller, input bandwidth model, or buffer-capacity auditor.

## Identity and multiplicity

An initial event is identified by its zero-based occurrence index in the
input tuple passed to `run_network_v0`. Two identical events at the same
logical timestamp are two distinct occurrences, with independent arrival
boundaries. The plan must bind **every** occurrence exactly once; indices
are strictly ordered and contiguous after binding.

## Arrival boundary

`arrival_boundary >= 0` is an explicitly supplied `SERVICE_TIME` boundary.
It is not computed from the event's logical timestamp or propagation delay.
No physical external-input cost is implied. The event becomes logically
available for service starting at that boundary.

`BatchIngressReleaseV0.ready_boundary` is the maximum arrival boundary of
external events participating in the batch. A batch with no external events
has release boundary zero. This is only an **external-input constraint**;
routed predecessors and state/program dependencies are modeled separately.

## Invariants

- No spike occurrence is deduplicated, discarded, or manufactured.
- Every initial event maps to exactly one observed consuming batch.
- The batch and PE are resolved using the logical access plan and catalog.
- The per-batch initial multiplicity must match Event Provenance v0.
- Ingress binding does not change `EVENT_TIME` or the frozen network result.

## Next integration gates

1. A release-aware service scheduler must enforce each consuming request's
   release boundary before allocating any service units.
2. The buffer audit must account for each event at its specified arrival
   boundary rather than preloading all events at boundary zero.
3. A later controller must specify input transaction costs, bounded-buffer
   admission and backpressure without silently dropping events.

This version deliberately does not imply that the existing S3.5 schedule
already respects these new release constraints.
