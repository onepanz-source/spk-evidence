# SPK S3.7d/3b2b2k/6: Owned Internal State Commit v0

## Purpose

Close the complete internal-service loop **for Core batches that produce no
candidate output spikes**. The frozen Core computes the next neuronal state;
a single owner of `OwnedInternalReadStateV0` certifies a real consumed EVENT
batch, confirmed PROGRAM_REFERENCE and STATE_LOAD, the exhausted STATE_COMMIT
service, and all serialized causal predecessors. Only then may it update the
versioned neuronal S image and confirm STATE_COMMIT in the Service Quantum.

This is deliberately **not yet** the atomic STATE/OUTPUT transaction. Any
candidate Core output means the commit MUST fail closed until the future
single-owner transaction can reconcile and atomically admit OUTPUT effects.

## Interface and invariants

`commit_owned_internal_state_v0(network, manifest, requests, graph, state, *,
commit_request_id)` returns `OwnedInternalStateCommitStepV0` with an immutable
updated state and an `OwnedInternalCommitEvidenceV0`.

1. The graph must already include every serialization edge computed by
   `serialize_internal_access_graph_v0`. Earlier same-neuron STATE_COMMIT must
   be confirmed before the subsequent STATE_LOAD.
2. STATE_COMMIT must be in `awaiting_confirmation` after genuine service
   exhaustion. The prepared Core result must belong to exactly the witnessed
   `BATCH_CONSUME` and the corresponding confirmed PROGRAM_REFERENCE and
   STATE_LOAD. Their target, node, PE, EVENT_TIME and epoch must agree.
3. Routed/external occurrence identities are checked against the controller's
   retained consumed tombstones and binding manifest. The precise channels,
   including multiplicity, are reconstructed from those bindings.
4. A prepared transition with any output candidates is *rejected*, not
   silently committed. `commit_core_transition_v0` independently recomputes
   the frozen Core transition against the current S version. The S update and
   `ServiceQuantum.confirmed` update are constructed in the same immutable
   owner result; the source state is never changed in place.
5. Every later owner tick replays the entire locally retained Core commit log
   from the frozen initial state, checks each commit receipt and saved P/S
   reading against its original version, and rechecks retained EVENT evidence.
   A previously committed batch must never be re-prepared or replayed.
6. The commit function itself does not advance SERVICE_TIME; successive
   service ticks continue through `advance_owned_internal_reads_v0`.

## Explicit limitations

* The ordinary emission-producing neuronal path is deliberately blocked.
  Atomic STATE_COMMIT plus OUTPUT reservation/publication remains a required
  next development; no premature state write or spike emission is permitted.
* Active PROGRAM memory is still the immutable program in `NetworkV0`, not a
  separate byte-addressed P store.
* The routing manifest was generated upstream; this module is not yet an
  independently routed whole-network executor.
* Retained tombstones and full replay of the Core history are not a bounded
  retention or cryptographic anti-replay protocol. These results validate
  local owner-state transitions under the normal simulator ownership model,
  not arbitrary hostile reconstruction of all internal dataclasses.
* This owner handles only the regular P/S/BATCH/STATE_COMMIT path. Learning,
  snapshot and candidate-program writes are excluded. No deadlock claim.

## Acceptance

The package has five files: **two modifications** of previously validated S3
Owned Internal Reads module/documentation, and **three new files** for this
component. Frozen Core v0, Network v0 and Compiler v0 are not modified.

```
python -m pytest -q tests/test_owned_internal_state_commit_v0.py
python -m pytest -q tests/test_owned_internal_reads_v0.py tests/test_serialized_internal_graph_v0.py tests/test_owned_internal_state_commit_v0.py
python -m pytest -q
```

The local reconstructed integration environment passed 466 tests, including 33
new commit-specific tests. It uses substitute low-level Core/Network models;
those checks are not equivalent to the real fwork suite. Expected real suite
count after the previously reported 1,583 is **1,616**. Fix any real-API
mismatches without weakening its contract; no commit before all tests pass.

## Next work

Design **single-owner atomic STATE/OUTPUT commit**: reserve the entire computed
fan-out, ensure the actual controller accepts its publication, then commit
neuronal state and certify emission without a split-brain intermediate result.
Check independent equivalence against the frozen Network v0 for emitting
and non-emitting batches. Diagnose genuine deadlocks only after service-time,
ingress release and resource progress are observed over the full state.
