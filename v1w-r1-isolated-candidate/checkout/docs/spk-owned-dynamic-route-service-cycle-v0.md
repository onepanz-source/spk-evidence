# SPK S3.7d/3b2b2k/19: Owned Dynamic Route Service Cycle v0

## Scope

This is a **routed-only dynamic-lane integration**, not an authoritative
scheduler for the entire neuronal network. It composes the already-tested
`OwnedDynamicRouteTransitStateV0` and `advance_service_quantum_v0` with a
persistent **finite EVENT slot claim** per dynamic route.

No frozen Core, Network, or Compiler module is modified.

## State

`OwnedDynamicRouteServiceCycleStateV0` contains an immutable `transit`
(registration ledger, routed storage and service quantum) and a sorted tuple of
`reserved_route_request_ids`. Each reservation is for exactly one slot in the
destination PE's EVENT domain. The invariant is, for every PE:

```
EVENT_resident(PE) + dynamic_EVENT_reserved(PE) <= PE.event_slots
```

Reservations exist only for registered dynamic `ROUTE_ENQUEUE` requests whose
identical event IDs are physically present in source `OUTPUT`. Partial and
service-finished dynamic routes must retain reservations until their physical
`OUTPUT -> EVENT` transfer completes. This precludes another route from
claiming the same free capacity during multi-tick service.

There is no phantom queue, no reservation of external storage, and no guarantee
that a preexisting caller-created initial snapshot has an authenticated history.

## One service tick

`advance_owned_dynamic_route_service_cycle_v0(state)`:

1. Revalidates the joint immutable snapshot, occupancy, provenance and service
   state.
2. Scans registered, *physically published* routes in stable ID order. When
   source emission is confirmed and an EVENT slot is free, obtains a persistent
   claim at the destination PE. A route blocked by capacity receives **no**
   service-start grant.
3. Passes **only new finite claims** as `granted_memory_request_ids` to the
   existing Service Quantum. Earlier partial requests retain their claims.
4. Rejects the tick if it would expend service units for a nonroute operation.
   The internal P/S and source-emission authorities own those effects.
5. Passes work-finished requests to the existing dynamic route transit, which
   commits real physical delivery and confirms route service only after that
   delivery.
6. Retires claims on physical delivery and returns a single immutable
   successor. Any exception leaves the caller's snapshot unchanged.

`EVENT_TIME` comes from the immutable occurrence, whereas the quantum increments
`SERVICE_TIME` by one. **Equality of their numeric values does not merge them.**

The limited lane handles all routes bound by the registry and does not infer
completion from idle ticks, automatically consume destination batches or mint
additional Core emission IDs.

## Explicit non-goals and trust boundary

- Initial publication of the source emission and its service confirmation must
  already be produced by the source owner. The cycle *checks* their consistency
  with storage, but cannot independently authenticate arbitrary supplied history.
- All preexisting base requests that could otherwise consume PE service must
  be controlled by their own authority: this cycle rejects service slices for
  them rather than silently advancing a P/S operation.
- External EVENT occupants are **not modeled** in the routed storage snapshot.
  The capacity proof is sound only for a *closed routed-only lane*. A unified
  EVENT ledger that includes external ingress and other owners is still needed.
- Source allocations can remain `STAGED` and dynamic routes are **not yet bound
  to destination `BATCH_CONSUME` requests**. Successfully moving an occurrence
  to `EVENT` is not a batch-closure proof or consume authorization.
- No terminal-only output handling, no global snapshot single-owner protocol,
  and no deadlock proof are provided.

## Acceptance checks

The accompanying tests cover multi-tick service, parallel occurrences, finite
reservations, static EVENT occupancy, recovery after space becomes available,
service-before-delivery exclusion, causality, immutable replay, snapshot
resume, invalid claims, and refusal of unrelated P/S service.

Recommended regression commands:

```sh
python -m pytest -q tests/test_owned_dynamic_route_service_cycle_v0.py
python -m pytest -q tests/test_owned_dynamic_route_service_cycle_v0.py tests/test_owned_dynamic_route_transit_v0.py tests/test_causal_service_quantum_v0.py
python -m pytest -q
```

Next: converge source emission commitment, this dynamic lane, and external EVENT
ownership into one authoritative scheduling snapshot; only then bind dynamic
routes to destination batches and attempt certified causal closure.
