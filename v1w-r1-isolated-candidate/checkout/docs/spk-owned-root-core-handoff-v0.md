# SPK S3.7d/3b2b2k/23: Owned Root Core Handoff v0

## Purpose

Connect **the actual physical consumption** of a sealed root batch in the
shared finite EVENT ledger to a canonical `WitnessedCoreInputBatchV0`. This
is not an independent service authority or a general neuron scheduler.

`advance_owned_root_core_handoff_v0(state)` owns exactly one `SERVICE_TIME`
boundary by delegating to `advance_owned_root_batch_consumption_v0`. It creates
new Core input witnesses only when that owner physically moves the *complete*
sealed batch to external-input tombstones and confirms `BATCH_CONSUME` service.
It retains the witnesses in the next immutable snapshot, with exact coverage
over the physical tombstones and no double consumption.

A read-only `preview_witnessed_root_core_v0` invokes frozen Core semantics
with **only** channels derived from those real consumed occurrences. It is a
candidate computation for independent testing, **not** an authorized `P/S`
read or `STATE_COMMIT`. Its caller-supplied versioned image is validated against
the same epoch and network but is NOT authenticated as a real `STATE_LOAD`.
No output publication or neuronal state update takes place.

## Preconditions and invariants

- The external epoch is finite and sealed, trusted at creation.
- The neuron has no incoming network edges; other nodes are rejected.
- Complete physical consumption precedes any generated witness.
- Each witness matches the exact external occurrence indices, `EVENT_TIME`,
  target PE, channels and `BATCH_CONSUME` identity.
- Historical witnesses correspond exactly to tombstones and confirmed service;
  multiplicity of repeated channels is preserved.
- `EVENT_TIME` and `SERVICE_TIME` remain independent dimensions.
- Every function is pure; on error the input state is unmodified.
- Previously forged/externally supplied snapshots remain outside this module's
  trust proof. The initial owner state must be installed by a trusted scheduler.

## Exclusions

- No automatic `PROGRAM_REFERENCE`, `STATE_LOAD` or `STATE_COMMIT` service.
- No mutable P/S memory, no authenticated Core results or OUTPUT admission.
- No routed-event consumption, nonroot closure or deadlock classification.
- No general shared service scheduler. This is a witnessed handoff with a pure
  calculation *preview* on the supported root path only.

## Acceptance

Run `pytest -q tests/test_owned_root_core_handoff_v0.py`, then the full suite.
Only after fwork validates should the three new files be committed.
