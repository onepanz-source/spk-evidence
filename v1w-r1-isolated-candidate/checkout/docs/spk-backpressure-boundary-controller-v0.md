# SPK S3.7d/3b1: Backpressure Boundary Controller v0

Status: **candidate**, pending full suite on the real SPK repository.
Scope: `spk_simulator/backpressure_boundary_v0.py`, downstream of frozen Core v0, Network v0 and Compiler v0.

## Purpose

Connect the already verified finite-slot reservation ledger and the S3.7d/3a
route arbiter at an explicit `SERVICE_TIME` boundary. The transition is
**pure and serial**: it returns a new immutable state or fails without changing
the supplied state. Route identifiers are **occurrences**, not payload keys.

This module does **not** implement the causal service scheduler itself.
The caller supplies independently verified completed service operations and
newly eligible `ROUTE_ENQUEUE` IDs. Its actions are **not authenticated against**
`CausalScheduleResultV0` or `AccessDependencyGraphV0`. In particular, it
cannot establish that an `OFFER` follows `EMISSION_RECORD` or a `COMMIT`
follows completed route service. Connecting these is S3.7d/3b2.

## API

`advance_backpressure_boundary_v0(architecture, manifest, state, *, service_boundary, actions)`

- `BackpressureBoundaryStateV0(storage, ledger, arbiter)`
- `BackpressureBoundaryActionsV0(route_consumptions=(), external_consumptions=(), route_commits=(), external_arrivals=(), routed_offers=(), newly_ready_routes=())`
- Result includes new state, ordered operations, granted routes, denied routes and per-PE occupancy.

The caller owns the state and must adopt the returned state before advancing
to another boundary. Boundaries increase strictly; arbitrary gaps are
allowed only when **no bound external arrival is silently skipped**.

## Boundary precedence

For each explicit service boundary, transitions run in this order:

1. **CONSUME_ROUTE**, **CONSUME_EXTERNAL**: free resident E slots.
2. **COMMIT**: reserved E slot becomes resident; OUTPUT is freed atomically.
3. **ARRIVE_EXTERNAL**: non-backpressurable inputs must arrive at their exact
   pre-bound `SERVICE_TIME`, never earlier, later or silently omitted.
4. **OFFER**: output-own a provenance-bound routed occurrence, consuming one
   finite `output_slots` slot.
5. **RESERVE / WAIT**: the S3.7d/3a arbiter serializes claims. Existing waiters
   precede newly ready routes. Denied routes remain in source OUTPUT.

An admitted route or an external occurrence may not be consumed at the same
boundary as its admission or arrival, respectively. Reservation and route
commit likewise cannot occur at the same boundary.

## Capacity and conservation

For each PE, both of the following are maintained by the existing ledgers:

`pending_output <= output_slots`

`routed_admitted + external_resident + reserved_routes <= event_slots`

One occupied OUTPUT slot remains responsible for a routed occurrence while
its destination event slot is reserved. Commit changes ownership atomically.
`WAIT` entries are identifiers only, not an extra payload queue.

Invalid actions, non-backpressurable ingress overflow, and output overflow
are **explicit failures** of the proposed transition, with no partial state
mutation. `BoundaryCapacityDeniedV0` exposes reason, occurrence ID, PE and
`SERVICE_TIME` boundary. A denied route reservation, unlike an overflow,
returns a valid state and can be retried later.

## What is still missing

- Source-level service suspension when OUTPUT is full: current OFFER fails
  closed; it does **not** suspend `EMISSION_RECORD`.
- A live causal scheduler that generates and authenticates actions and does
  not grant service units to blocked routes.
- Bounded progress/deadlock classification across dependencies and PEs.
- Concurrent hardware execution semantics (current state-owner is serial).
- A bounded retention policy for diagnostic tombstones after each epoch.
- Explicit ingress-buffer modeling for external streams that require
  backpressure. Such streams remain non-backpressurable here.

`EVENT_TIME` is never altered or used to infer a `SERVICE_TIME` boundary.
This module does not modify the frozen APIs or functional neuronal results.

## Validation

The package includes 39 tests covering normal route lifecycle; old waiters;
shared external/routed capacity; no input omission; output overflow and
non-backpressurable ingress rejection; monotonic boundaries; same-PE transfer;
conservation; deterministic ordering; and rejection of duplicate, unknown or
invalid occurrences. Passing them does not imply the live scheduler is done.
