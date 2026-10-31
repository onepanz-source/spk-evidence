# SPK S3.7d/3b2b2k/3: Witnessed Core Input v0

**Status: EXPERIMENTAL.** This is not a release of the complete autonomous scheduler.

## Purpose

Perform one bounded, autonomous storage service tick and reconstruct the **exact
consumed Core batch** from actual `CONSUME_ROUTE` and `CONSUME_EXTERNAL`
boundary operations, through `ServiceEffectAuthority` and
`Causal Service Quantum`. The caller does not provide event channels, fake
consumed IDs, a driver frame, or confirmed request IDs.

`advance_witnessed_core_input_tick_v0(...)` returns both the prior
`AutoFramedOwnedTickV0` result and a tuple of immutable
`WitnessedCoreInputBatchV0` records. For each completed `BATCH_CONSUME`, it
checks request identity, EVENT target, PE, epoch, event time, quantity, channel
multiplicity, and complete coverage of all bound routed/external identities.
Routed IDs and external indices remain **separate namespaces**. `SERVICE_TIME`
records the boundary of physical consumption; `EVENT_TIME` comes from the
original event occurrences, not from service time.

## Important non-claims

- A witnessed input record is **not** a `PROGRAM_REFERENCE`, `STATE_LOAD`, or
  `STATE_COMMIT` authorization. This function does not write neuron state, call
  `run_core_batch`, or publish output spikes.
- The route manifest is still bound from a reference functional trace; this
  adapter does **not** establish trace-independent generation of outgoing
  spikes. It is the input boundary to the future versioned Core owner.
- A caller can still construct Python dataclass objects that resemble a valid
  history. The secure claim here is relative to the state owned by the existing
  pure bounded controller and its *executed* transitions, not protection
  against arbitrary fabrication of the controller's initial snapshot.
- Storage-only service execution remains the domain of this function; internal
  service kinds require their own semantic authority and integration before
  autonomous multi-node execution can be claimed.

## Following gate

A single owner must combine witnessed input, versioned Core memory, serviced
`PROGRAM_REFERENCE` / `STATE_LOAD`, and deferred `STATE_COMMIT` with output
admission. Network v0 remains an **independent validation oracle**.

Frozen Core / Network / Compiler v0 are not modified.

## Read-only Core staging

`advance_and_stage_witnessed_core_tick_v0` optionally performs the **actual
frozen Core calculation** using the exact witnessed channels and a separate
`VersionedNeuronImageV0`. The resulting `PreparedCoreTransitionV0` remains
speculative. No `STATE_COMMIT`, no service confirmation, no `OUTPUT` publication.
The input image belongs to the caller until the future single-owner runtime is
completed. To avoid presenting two conflicting same-neuron preparations from
one version, staging refuses more than one same-neuron batch per service
boundary. No shortcut around P/S service is implied.
