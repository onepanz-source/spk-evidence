# SPK S3.7d/3b2b2c: Causal Service Frontier v0

Status: DRAFT / independent verification required on fwork.

## Purpose

One deterministic, read-only eligibility classifier for a given SERVICE_TIME
boundary. All Core v0, Network v0 and Compiler v0 semantics remain frozen.
It consumes an existing dependency DAG, service requests, optionally validated
external ingress releases, and explicitly authenticated memory grants supplied
by the future owner-scheduler.

## Classification precedence

1. COMPLETED, IN_FLIGHT: never offered for new service.
2. DEPENDENCY: any predecessor not yet completed.
3. RELEASE: an external batch cannot start before its SERVICE_TIME release.
4. MEMORY: EMISSION_RECORD or ROUTE_ENQUEUE without a memory grant.
5. READY: all three preconditions satisfied.

The classifier refuses cyclic graphs, incomplete dependency coverage, unknown
PEs/requests, an impossible completed/running causal snapshot, malformed
external release coverage and conflicting memory grant assertions.

## Guarantees

- Does not change `EVENT_TIME`, infer SERVICE_TIME from EVENT_TIME, or mutate
  any input snapshot.
- Does not interpret a missing grant as an actual allocation or failure.
- Does not silently make a ROUTE_ENQUEUE or EMISSION_RECORD READY without
  a caller-supplied grant.
- Does not conflate a waiting request with a deadlock.
- Returns canonical request-id ordering independent of input tuple ordering.

## Critical limitation

This component **does not independently authenticate** the caller's completed,
in-flight or granted service identifiers. A later owner-scheduler MUST derive
these from its own actual PE service counters and from the bounded buffer
controller. No bandwidth is consumed, no memory is reserved, and no request is
completed here. Ready items are candidates only; they are not a schedule.

## Next development

Implement a single-owner service-cycle state machine: advance service-unit
counters on available PEs, feed authenticated route/emission grants from the
boundary controller, and derive causal completion events that update this
frontier. Keep a finite progress horizon and classify resource deadlock only
when no future arrival or independently finishable service can release a wait.
