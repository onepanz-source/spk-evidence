# SPK S3.7d/3b2b2k/7: Computed Emission Binding v0

## Reason for this checkpoint

The now-validated *Owned Internal State Commit* supports **non-emitting** Core
batches. Enabling emitting batches is not a matter of removing its `candidate_outputs`
guard. The storage-only replay plan/`AtomicEmissionAdmissionV0` was generated
from an upstream functional trace, not from this owner’s independent Core computation.
One local regression fixture demonstrates the gap: the Core produces a candidate
spike for neuron **B**, but the existing `AtomicEmissionAdmissionV0` only
contains groups emitted by **A** and **C**. Any code claiming atomic STATE/OUTPUT
for B with that admission would either invent OUTPUT or acknowledge nonexistent
storage resources.

## Function

`bind_computed_emission_v0(architecture, network, image, prepared, manifest,
admission, requests, *, emission_request_id)` verifies one Core emission
**before** any architectural side effect and returns an immutable
`ComputedEmissionBindingV0`.

The function:

1. Re-executes the frozen Core `prepare_core_transition_v0` from the current
   versioned image and rejects altered/precomputed candidate outputs or state.
2. Requires a matching `EMISSION_RECORD` service request and atomic admission
   group for the actual **source neurone, EVENT_TIME, epoch and PE**. The
   target must be `outputs:<source_node>`, with quantity equal to the number
   of computed output occurrences, preserving multiplicity.
3. Expands each Core candidate output through `NetworkV0.edges`; matches the
   complete expected multiset to the admission group's bound route identities
   and their destination, channel, delay and emission/delivery times. Parallel
   or identical edges remain separate occurrences.
4. Rejects incomplete/overlapping manifest claims and invalid finite OUTPUT
   group capacity. Does not interpret `EVENT_TIME` as `SERVICE_TIME`.
5. Records terminal candidate channels with no matching network edge, but does
   not pretend that they were already delivered to a terminal output.

## Important limitation

This is a **provenance and consistency gate**, not an atomic transaction, service
start grant, OUTPUT allocation, state update or publication receipt. It does
not construct the route manifest dynamically and does not independently attest
that the supplied upstream manifest faithfully represents a network execution.
No caller can use the returned binding to confirm `EMISSION_RECORD` or
`STATE_COMMIT` without the existing authoritative storage and service owners.

The next step is to add a **single-owner STATE/OUTPUT transaction** that obtains
an actual reservation for this exact Core fan-out, executes an OUTPUT boundary,
checks the complete publication evidence, then constructs **one returned
immutable successor** containing both new neuronal S and storage/quantum state.
Failure must leave the old snapshot unchanged. The commit-history replay audit
must then validate OUTPUT evidence as well as the existing S receipts.

The test fixture itself cannot serve as a positive B emission transaction until
its declared `EMISSION_RECORD`, routing bindings and causal requests are rebuilt
from the **computed** B output, rather than from the prior A/C trace.

## Acceptance

```
python -m pytest -q tests/test_computed_emission_binding_v0.py
python -m pytest -q
```

39 dedicated tests passed locally in a reconstructed compatibility environment
with substitute low-level Network and Architecture classes. The authoritative
check is the real `fwork` suite. Expected new total is **1,655** from the user's
validated 1,616 baseline. Nothing in Core v0 / Network v0 / Compiler v0 is
modified. The component must not be committed before real tests pass.
