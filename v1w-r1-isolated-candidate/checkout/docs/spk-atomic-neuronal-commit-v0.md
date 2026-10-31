# SPK S3.7d/3b2b2k/8 · Atomic Neuronal Commit v0

## Scope and design contract

This checkpoint implements an **immutable, indivisible successor state** for a
Core batch that produces at least one **routed** output. It coordinates the
existing finite-OUTPUT start ledger, authenticated bounded controller, Core v0
recomputation and versioned neuronal state commit. No state is returned if any
validation, storage offer or Core commit fails.

It does **not** provide a general self-running network executor, and it does
not independently generate the routing manifest or admission groups. Those
still originate from upstream plans/traces. The independent frozen Core is
recomputed in this transaction, rather than trusting an observed Core result.

## Transaction and fail-closed requirements

1. Check canonical serialized neuron state dependencies and actual completed
   service for the corresponding `STATE_COMMIT` and `EMISSION_RECORD`.
2. Rebuild P/S/consumed-EVENT causal evidence from controller history. Ensure
   the read `version` equals the current version, and that the prepared Core
   transition has the correct `EVENT_TIME`.
3. Bind independently computed Core candidate outputs to the complete declared
   routed fan-out using `bind_computed_emission_v0`.
4. Require an already-owned *finite OUTPUT start reservation* for the complete
   group. A speculative free-slot count is **not** a start grant.
5. Submit the emission to the existing owned service tick at its current
   `SERVICE_TIME`; require a real `OFFER` of every routed occurrence and the
   authenticated `EMISSION_RECORD` confirmation.
6. Commit the recomputed Core state against the original, versioned memory.
   Confirm `STATE_COMMIT`, retire preparation, record receipt and the paired
   computed output binding, then audit the complete new history.
7. Return **one** immutable `OwnedInternalReadStateV0` containing both effects.
   Intermediate proposals remain local and are never exposed to the caller.

A failed transaction raises without modifying the prior frozen snapshot.

## Coordinated changes to prior components

- `owned_service_autoframe_v0.py`: two backward-compatible opt-in parameters
  permit an owned internal `STATE_COMMIT` to remain awaiting confirmation and
  withhold the associated emission from the legacy autonomous storage publisher.
  Existing standalone storage callers retain the previous fail-closed behavior.
- `witnessed_core_input_v0.py`: forwards these opt-in policies to the owner.
- `owned_internal_reads_v0.py`: derives emission deferral from *declared*
  `STATE_COMMIT` batch identities, not caller-supplied completion IDs. The
  historical audit replays Core commits including routed-output commits when
  it receives the required architecture, manifest and admission. Emitting
  commits are invalid without authenticated OUTPUT history.
- `atomic_neuronal_commit_v0.py`: the sole new atomic commit entrypoint.

`spk_core`, `spk_network`, `spk_compiler` and their frozen baselines remain
unchanged. The earlier output-free `commit_owned_internal_state_v0` path is
unchanged.

## Explicit limitations

- **Terminal-only** emissions (without routed occurrences) are rejected. A
  separate terminal-output journal/contract is required before supporting them.
- A routing manifest and its admission groups are still supplied, potentially
  from functional replay. The result does not establish independent
  end-to-end network semantics, dynamic routing discovery or deadlock freedom.
- Service throughput, `EVENT_TIME` and `SERVICE_TIME` remain distinct.
- The transaction returns atomically in the *pure immutable architectural
  state model*. This is not a claim of persistent crash-safe multi-device
  atomicity.
- In a live deployment, the entire service advancement must use the owned
  internal path; standalone legacy storage ticks must not be interleaved by an
  unrelated owner with these stateful Core batches.

## Regression gate

```bash
python -m pytest -q tests/test_atomic_neuronal_commit_v0.py
python -m pytest -q \
  tests/test_owned_service_autoframe_v0.py \
  tests/test_witnessed_core_input_v0.py \
  tests/test_owned_internal_reads_v0.py \
  tests/test_owned_internal_state_commit_v0.py \
  tests/test_atomic_neuronal_commit_v0.py
python -m pytest -q
```

No Git commit before the *real fwork* suite is fully green and the intended
updates to existing files have been reviewed.
