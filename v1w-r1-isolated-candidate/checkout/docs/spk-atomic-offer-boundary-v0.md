# SPK S3.7d/3b2b2a: Atomic Offer Boundary v0

Status: candidate; validation on the real fwork repository required.

## Scope

`advance_atomic_offer_boundary_v0` composes two previously verified
components without changing them:

1. `plan_atomic_emission_offers_v0` chooses complete `EMISSION_RECORD` output
   groups that fit the *currently occupied* finite source `output_slots`.
2. `advance_backpressure_boundary_v0` executes one explicitly identified
   `SERVICE_TIME` boundary with consumption, commit, external arrivals,
   atomic routed offers, and route claim arbitration.

Inputs include a caller-authenticated list of *causally ready* emission IDs
and route IDs. A blocked emission **is not completed**. Its pending work is
owned by the future service scheduler, not stored in an unlimited implicit
queue. The returned immutable result reports which groups must be retried.

Previously blocked ROUTE_ENQUEUE requests are retained by the bounded
controller's arbiter state and are retried at future boundaries. Their spike
occurrences remain owned by the finite source OUTPUT storage until delivery.

## Phases and capacities

At service boundary `s`:

- Select complete atomic emission groups using PRE-BOUNDARY OUTPUT occupancy.
- Reject a request to start routing if its output is neither previously
  retained nor newly admitted for publication at this boundary.
- Delegate to the boundary controller, which applies its established phases:
  `CONSUME`, `COMMIT`, `ARRIVE_EXTERNAL`, `OFFER`, `RESERVE/WAIT`.
- Publish no partial atomic emission group. A failure of the controller
  raises an exception without returning a new state snapshot.

**Conservative deferral**: OUTPUT freed by a COMMIT *at* boundary `s` is not
reused for a newly offered emission until boundary `s+1`, because the planner
checks pre-boundary occupancy. This can reduce throughput and is not an optimal
scheduling claim. EVENT space from a same-boundary CONSUME *is* available to
routing reservations when the controller runs.

The frozen Core/Network semantics and `EVENT_TIME` are not changed.
All memory capacities are PE architectural capacities, not Python host RAM.

## Validation and trust boundary

The caller MUST authenticate that:

- An `EMISSION_RECORD` is causally ready and eligible for completion;
- route `ROUTE_ENQUEUE` requests are causally ready to begin service;
- route commits/consumptions correspond to completed service requests;
- external arrival/consume operations follow the validated ingress binding.

This component does not read the dependency DAG and does NOT enforce these
preconditions by itself. The underlying controller checks occurrence identities,
ledger integrity, reservation ownership, event slot capacity, and exact due
external arrivals. Unknown/invalid identities fail closed.

A zero-fanout emission produces no routed occurrence. Its single-completion
bookkeeping must be supplied by the future scheduler: this component returns
its admission but cannot remember it through OUTPUT storage.

## Non-goals / not yet implemented

- Active request scheduling, partial work/service units, PE bandwidth replay.
- Persistence and retry of *blocked emissions* across cycles by a scheduler.
- Dynamic deadlock detection and liveness guarantees.
- Parallel multi-owner mutations/true hardware atomicity.
- Physical transit/interconnect buffer, backpressurable external ingestion.

A finite cycle limit is not, by itself, proof of deadlock.

## Follow-up

S3.7d/3b2b2b should introduce a **single-owner multi-cycle scheduler** with
explicit per-request progress, causal DAG, PE service bandwidth, retained
blocked emissions, bounded retries, and distinct `WAIT_FOR_ARRIVAL`,
`WAIT_FOR_OUTPUT`, `WAIT_FOR_EVENT_SLOT`, `DEADLOCK`, and `SERVICE_LIMIT` states.
End-to-end traces must be reconciled with `Schedule-to-Boundary Bridge` and
the frozen Network observer before a release claim.

## Tests

`python -m pytest -q tests/test_atomic_offer_boundary_v0.py`

A broader compatibility check should include atomic offer planning, the
boundary controller and the bounded route arbiter. Core, Network, and Compiler
v0 must not be edited.
