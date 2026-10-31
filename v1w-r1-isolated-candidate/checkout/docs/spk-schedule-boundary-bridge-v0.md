# SPK S3.7d/3b2a: Schedule-to-Boundary Bridge v0

Status: experimental simulator extension, not frozen.

## Purpose

Reconcile completed S3.5 release-aware causal service slices with the
single-owner S3.7d/3b1 finite-resource boundary controller, without changing
Core, Network or the frozen Compiler v0.

This is a **post-hoc admission gate for a fixed service schedule**, not an
active backpressure scheduler. It rejects a service trace that starts a route
whose event slot was not actually reserved at its start boundary. It does not
repair such traces, re-order instructions, or prove inevitable deadlock.

## Construction

1. Validate all service work and capacity claims through S3.7d/2, preserving
   the separately validated functional provenance of the route manifest.
2. Derive `OFFER` at source `EMISSION_RECORD` completion, `RESERVE` at the
   first slice of `ROUTE_ENQUEUE`, `COMMIT` at route completion and `CONSUME`
   at target `BATCH_CONSUME` completion.
3. Bind every external arrival to its independently declared SERVICE_TIME
   boundary, never to its neuronal EVENT_TIME.
4. Replay all boundaries from 0 through the last transition using the
   S3.7d/3b1 controller. Every route in service must actually have a claim.
5. Compare final event residency, consumption and claims with S3.7d/2.

## Constraints and limitations

- S3.7d/3b1 determines phase ordering and external-ingress precedence.
- Homogeneous PE capacities remain mandatory in Architecture v0.
- No silent event drop, deduplication, or unlimited pending storage.
- No mutation of the caller's schedule, inputs, event timestamps, or state.
- All routing occurrences retain separate identities, including parallel edges.
- Rejected trace != proof that every possible alternate schedule fails.
- No concurrent PE execution, producer suspension, automatic retry or deadlock
  detector is implemented in this checkpoint.
- `max_boundaries` bounds memory and replay duration even with sparse inputs.

## Acceptance

The bridge must pass test cases for deterministic replay, parallel spike
multiplicity, delayed external arrivals, same-PE routing, empty networks,
invalid input types, finite boundary limit and tampered service schedules.

The next step is a distinct live scheduler that calls this controller before
servicing a route or publishing an emission, with bounded progress/deadlock
failure modes. The frozen S3.5 scheduler stays intact.
