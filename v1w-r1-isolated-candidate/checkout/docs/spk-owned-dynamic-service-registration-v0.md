# SPK S3.7d/3b2b2k/11 · Owned Dynamic Service Registration v0

Status: **candidate** until the real fwork full-suite gate has passed. This file does not modify frozen Core v0, Network v0, or Compiler v0.

## Purpose

Convert an **independently computed Core emission** and the epoch-scoped identity allocation from k/10 into a *staged*, typed `MemoryServiceRequestV0` bundle and a complete, canonical dependency graph. The caller supplies **no emission or route request IDs**. IDs are allocated in the same immutable transition as request creation.

- `initialize_owned_dynamic_services_v0(architecture, network, placement, image, base_requests, base_graph, cost_policy, *, first_dynamic_request_id=None)`
- `register_owned_computed_emission_services_v0(state, image, prepared)`

`DynamicServiceCostsV0(service_profile_id, emission_units, route_units)` declares positive integer service costs. The model **does not infer hardware latency or claim that the numbers are calibrated**. An integrating scheduler must use its approved transaction mapping policy.

## Identity and causal invariants

For a computed candidate at `(epoch, node, EVENT_TIME, base_version)`, the owner reserves:

1. One `EMISSION_RECORD` ID, with `quantity == number of Core candidate outputs`, `target_id == outputs:<source node>`, source PE owner, domain `EVENT`, activity `EXECUTE`.
2. One `ROUTE_ENQUEUE` ID for *each physical edge occurrence* in the Core-derived topology, identical to its `RoutedOccurrenceV0.event_id`; target PE/node and logical emission timestamp derive from the frozen topology. Routing activity is `ROUTER`.
3. Dependencies `PROGRAM_REFERENCE`, `STATE_LOAD` and `BATCH_CONSUME` **→** `EMISSION_RECORD` **→** each `ROUTE_ENQUEUE`.

The new `EMISSION_RECORD` does **not** depend on `STATE_COMMIT`, because the atomic STATE/OUTPUT completion needs *both* services to finish before jointly confirming them. A dependency `STATE_COMMIT → EMISSION_RECORD` would create a liveness/authorization cycle.

The source batch must have a unique, serialized P/S/EVENT/STATE service group **already present** in the incoming requests and DAG. The base graph and original requests are preserved byte-for-byte as Python dataclass values, and all dynamic IDs are above the static ID namespace. All merged dependencies are sorted and validated for cycles and serialized neuron history. Invalid input raises without exposing a successor.

The immutable owner retains every allocation and registration, checking the historical one-to-one relationship between owned occurrences, typed service requests, and DAG predecessors. It rejects a second registration from an already-allocated neuron version. Earlier snapshots stay unchanged.

## Hard limitations: STAGED is not ACTIVE

**The result is not a runnable scheduler state.** In particular:

- It does not bind `ROUTE_ENQUEUE` to a destination `BATCH_CONSUME` or assign a `target_batch_index`. Routes can exist before the destination batch is actually formed. `unbound_route_request_ids` makes this explicit.
- It does not construct `RoutedBindingManifestV0`, `AtomicEmissionAdmissionV0`, OUTPUT grants, or live memory reservations; does not make the new requests eligible for `advance_service_quantum_v0`, `advance_owned_service_tick_v0`, or any boundary controller. Do **not** pass `staged_requests`/`staged_graph` as an activated input until destination ownership and admissions are established.
- It requires the source P/S/EVENT/STATE requests to exist. Generating **future neuron batches** dynamically from received events is a separate, still-open problem. Therefore this is **not** an autonomous network runtime.
- The existing `Atomic Neuronal Commit v0` still takes a complete routing/service manifest; this checkpoint does not modify that contract or claim to couple the new staging owner to physical publication.
- Only one outer authoritative scheduler must persist the **latest** immutable allocation snapshot. Forking an old snapshot can fork IDs. No cryptographic prevention is claimed.
- Terminal outputs produce an `EMISSION_RECORD` but no route requests. Terminal publication/accounting is not implemented.
- Staging history is unbounded host-side metadata; no bounded-history retirement policy is claimed.

## Acceptance tests

```bash
python -m pytest -q tests/test_owned_dynamic_service_registration_v0.py
python -m pytest -q
```

## Next integration

Create destination `BATCH_CONSUME` from *admitted EVENT* occurrences; bind the route identity and delivery provenance to the new batch, apply the real transaction mapping policy, then allow boundary admission of a complete request/manifest snapshot. Reconcile it with the atomic STATE/OUTPUT owner, and compare independently against frozen Network v0 *only during validation*, not in the runtime's decision loop.
