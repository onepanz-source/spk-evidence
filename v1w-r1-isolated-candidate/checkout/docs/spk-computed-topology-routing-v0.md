# SPK S3.7d/3b2b2k/9 · Computed Topology Routing v0

Status: **candidate**, subject to full validation on `fwork`.

## Purpose

Derive the *routing intent* of a neuronal emission directly from the frozen
Core computation and frozen Network v0 topology, without consulting
`ObservedExecutionV0`, `RoutedBindingManifestV0`, or a precalculated routing
trace. This reduces dependence on trace replay but **does not yet** replace
the scheduler's service-request/admission manifest.

Entry point:

`derive_computed_topology_routing_v0(architecture, network, placement, image, prepared, *, first_event_id, used_event_ids=())`

The caller supplies an admitted `PEAdmissionManifestV0` (static topology
placement), a versioned neuron image, a prepared Core transition and an
**allocation proposal**. The function itself re-runs frozen
`prepare_core_transition_v0` and rejects altered output channels, raw state,
version and timestamps.

## Derived intent

- One `ComputedRouteIntentV0` / `RoutedOccurrenceV0` per produced output and
  matching physical edge, including *each parallel edge* independently.
- Source and destination PE identities come from the admitted compiler
  placement, not an observed output manifest.
- The original `EVENT_TIME` and each Network edge's positive `delay_ticks`
  yield `delivery_event_time`; service cycles are not used as event times.
- Outputs on channels with no matching edge become `NetworkEventV0`
  `terminal_outputs`. These are **terminal intentions only**; they are not
  physically delivered or confirmed by this component.
- Output storage demand equals the number of routed occurrences. An atomic
  routed bundle greater than the source PE's `output_slots` raises
  `ComputedFanoutCapacityV0`; occupancy/reservations are not inferred.
- Routes use consecutive `event_id` values from `first_event_id`, in Core
  candidate order and deterministic per-edge order (target, channel, delay,
  original edge index). `next_event_id` is the proposed successor cursor.

## Strict limitations

This is a *pure candidate generator*, not an authoritative mutation of
routing state. In particular:

1. It does **not** generate `MemoryServiceRequestV0`, `AccessDependencyGraphV0`,
   `BoundRouteV0` or `AtomicEmissionAdmissionV0`. A destination batch's
   `consume_request_id` / `target_batch_index` **cannot be known** from the
   source spike alone.
2. It does **not** reserve output slots, authenticate source batch consumption,
   perform `STATE_COMMIT`, publish an output, deliver an event, or confirm a
   terminal output. `terminal_outputs` have no physical storage policy yet.
3. `first_event_id` is caller-supplied. `used_event_ids` detects overlap with
   *retained* history but cannot prove absence of IDs that have been retired.
   A future single-owner ledger **must atomically persist** `next_event_id`
   with a successful emission, and use an explicit epoch/retention contract.
   Running this pure function twice with the same cursor yields the same
   proposed IDs; this is not double publication.
4. The completed predecessor/service sequencing for new dynamically created
   requests, and their dependency/buffer controls, remain to be integrated.
5. Neither frozen Core nor frozen Network/Compiler implementation is changed.

## Next acceptance milestone

Integrate these computed intents into a single owner that dynamically creates
and authorizes service requests, binds target batch ownership when deliveries
occur, atomically advances the event-identity cursor on publication and
supports terminal outputs through a defined storage/observability policy.
Then compare independently generated executions against Network v0.

## Testing

`python -m pytest -q tests/test_computed_topology_routing_v0.py`

`python -m pytest -q`

The candidate contains 38 tests, including parallel edges, positive and
terminal outputs, PE placement, cursor policy, OUTPUT fan-out capacity,
malformed Core candidates and independent topology changes. The local
integration suite uses real SPK simulator modules with a *stub compiler*
manifest for compatibility checks. Passing that suite is not equivalent to
passing the complete `fwork` suite against the frozen compiler.
