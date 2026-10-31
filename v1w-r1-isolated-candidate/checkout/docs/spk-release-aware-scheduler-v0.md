# SPK Release-aware Causal Service Scheduling v0

Status: DRAFT - S3.6b/2
Baseline: spk-core-network-v0 (frozen)
Depends on: S3.5 Causal Service Scheduler and S3.6b/1 External Ingress.

## Contract

The finite, post-hoc causal scheduler accepts an optional
`ExternalIngressBindingV0` (`ingress=...`) and enforces
`BatchIngressReleaseV0.ready_boundary` for each BATCH_CONSUME request.

A ready request must satisfy BOTH conditions:

1. Every predecessor in its dependency DAG has completed at a prior
   service-tick boundary.
2. Its explicit external release boundary is no greater than the current
   SERVICE_TIME tick.

Every BATCH_CONSUME request needs a release record if `ingress` is supplied.
Routed-only batches have a zero external release and are still governed by
routing dependencies. Other request kinds have no external release in v0.

An event with EVENT_TIME 2 can arrive at SERVICE_TIME 12; there is no
implicit conversion between these temporal domains.

## Idle cycles and limits

With no ready work and a future release, the scheduler may jump directly
to that boundary, accounting for all skipped cycles as idle. Such cycles
count against `max_service_ticks`.

Completions at tick s unlock successors no earlier than tick s+1.
Independent PEs continue working while another PE awaits an external input.

## Scope and limitations

- Backward compatibility: `ingress=None` reproduces S3.5 scheduling.
- Releases are validated for coverage, multiplicity, identity, target PE,
  and explicit max-arrival boundary.
- Bindings are architectural inputs, not authenticated physical signals.
- The scheduler does not generate or enqueue the external events, enforce
  buffer occupancy, or model ingress bandwidth or backpressure.
- No changes to Core v0 / Network v0 behavior or EVENT_TIME.
- All requests and the provenance trace still exist before scheduling;
  this is NOT live event-driven execution.

## Acceptance gates

- Late input defers consumption and counts idle SERVICE_TIME.
- Duplicate initial spikes retain separate occurrence indices.
- Both routed dependencies and external releases are respected.
- Independent PE operation, deterministic replay, and service conservation.
- Incomplete, forged, or wrong-target ingress bindings are rejected.
- Zero ingress preserves S3.5 behavior and the full regression suite.

Passing finite tests does not prove formal equivalence.
