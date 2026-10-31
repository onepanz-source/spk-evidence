# SPK S3.7d/3b2b2d — Causal Service Quantum v0

Status: **DRAFT / implementation candidate**; requires full real-repository verification.

## Purpose

Spend **finite architectural service units per PE and per SERVICE_TIME tick**,
without inferring architectural time from neuronal `EVENT_TIME`. This component
starts the single-owner architectural service-work loop and composes the frozen
service dependency graph with `CausalServiceFrontierV0`.

It deliberately does **not** implement full active backpressure, PE arbitration
policy, authenticated storage commits, or deadlock detection.

## API and immutable service-work state

`advance_service_quantum_v0(architecture, requests, graph, state, *,
confirmed_request_ids=(), granted_memory_request_ids=(), ingress=None)`

`ServiceQuantumStateV0` separates three non-overlapping request states:

- `partial`: positive service units already spent, strictly less than the demand;
- `awaiting_confirmation`: demand exhausted at a known service boundary,
  but architectural effect not yet confirmed;
- `confirmed`: the caller attests that the physical/logical architectural
  operation was completed at the indicated boundary.

The fourth implicit state is **unstarted**. Request ids are unique and canonical.

The `ServiceQuantumStepV0` returns an immutable new state, one-unit service
slices, per-PE spent units, the frontier used for start eligibility, completed
work ids (not causal completions), and an `IDLE`/`WAITING`/`PROGRESSED` marker.

## Timing and dependency invariants

- A call operates at `state.next_service_tick`, starting at zero and increasing
  by exactly one each successful call.
- The total spent on each PE at tick `s` is bounded by
  `ProcessingElementV0.accesses_per_service_tick`.
- A request that exhausts its final unit during tick `s` has
  `finish_boundary = s+1`.
- **Finishing service is not completing the routed operation.** Only a separate
  `confirmed_request_ids` input can move a finished request to `confirmed`.
- A causally dependent request can start only after the predecessor has been
  confirmed. A dependency cannot be enabled by service exhaustion alone.
- A request with a valid partial service state is favored before an unstarted
  request on the same PE. Other requests are allocated deterministically by
  increasing `request_id`. Multiple available service units are distributed
  round-robin within the single tick, respecting demand.
- Independent PEs may spend service units in the same tick.
- `ExternalIngressBindingV0` is supplied explicitly. Its `arrival_boundary`
  governs eligibility; its `event_time` is never modified.
- `EMISSION_RECORD` and `ROUTE_ENQUEUE` may start only when the caller
  supplies a memory grant. The grant is **not authenticated** here.
- A partial request retains the start-of-service permission represented by
  its state; replaying a grant for an in-flight request is forbidden.

## Authority boundary

**Important:** Both `granted_memory_request_ids` and `confirmed_request_ids`
are still **caller claims**. Passing either does not prove that a reservation,
output publication, route commit or batch consumption really happened.

The next component must obtain these values from the actual single-owner
`BoundedBackpressureStateV0`/`BackpressureBoundaryResultV0` and validate their
lifecycle. The service quantum cannot yet be treated as a safe standalone
active scheduler, even when it returns `PROGRESSED`.

`WAITING` does not imply deadlock. Advancing a finite number of ticks without
progress does not establish that all future arrivals or dependency releases
are impossible.

## Release contract

This module adds new files only. It does not modify frozen `spk_core`,
`spk_network`, `spk_compiler` or prior `spk_simulator` modules. Regression
coverage should verify native constructors and `pytest` collection on fwork.

Acceptance checks: deterministic service allocation, per-PE bandwidth, strict
causal confirmation, delayed ingress, immutable state, explicit memory grants,
no repeated service after work exhaustion, no implicit event-time mapping.
