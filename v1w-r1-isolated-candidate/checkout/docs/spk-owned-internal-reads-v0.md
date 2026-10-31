# SPK S3.7d/3b2b2k/4 — Owned Internal P/S Reads and Core Preparation v0

## Scope

One immutable owner state integrates:

1. The **actual** SPK storage boundary / Service Quantum via `advance_witnessed_core_input_tick_v0`.
2. `PROGRAM_REFERENCE`: after the request's service has finished, read the frozen node's `config` and `program` from the active `NetworkV0` image.
3. `STATE_LOAD`: after the request's service has finished, read `(raw, last_timestamp, version)` from the versioned neuron image.
4. Promote **only these reads**, with their materialized values, from `awaiting_confirmation` to `confirmed` in the owner-maintained `ServiceQuantumStateV0`. New confirmations use the new service boundary, never an earlier one.
5. Accumulate actual `BATCH_CONSUME` witnesses; validate retained routed-consumption tombstones and external-consumption ledger IDs for previous batches. When the matching P/S reads exist, run `prepare_core_transition_v0` with the exact witnessed channels. Do **not** mutate neuron state.

No read evidence, completion IDs, input channels, or boundary frames are accepted from the caller as new per-tick claims.

## Strict restrictions

* Supported path is ordinary `PROGRAM_REFERENCE` and `STATE_LOAD` paired one-to-one with `BATCH_CONSUME` for each `(node, EVENT_TIME, target PE)` within a single epoch. Each pair has exactly one P and one S request. This is an intentionally **narrow profile** of the existing access schema, not a generic memory target mapper.
* The authoritative program in this preliminary active-P model is the *immutable* `NetworkV0` node configuration and Core program. It does not implement a physically distinct P-memory byte store, version changes, cache misses, or candidate-program writes. The service cost is still paid by the actual `ServiceQuantumV0`.
* The authoritative state read comes from the current `VersionedNeuronImageV0`. This component **never performs a STATE_COMMIT**. After an authorized output-free `STATE_COMMIT`, historical state-read receipts remain bound to their original version and are rechecked against a replayed immutable Core commit history. Uncommitted reads must still match the **current** version. `OwnedInternalReadStateV0.commits` retains those history records. The complementary `owned_internal_state_commit_v0.py` performs the actual commit for the restricted no-output case; the general STATE/OUTPUT atomic transaction remains open.
* Each pending EVENT witness is rechecked against actual **retained** consumed-route and consumed-external identities. Retaining these tombstones indefinitely is not a long-term storage policy; bounded retention/replay-proof checkpointing remains open.
* One prepared, **uncommitted**, Core transition per neuron is allowed at a time. Later batches for that neuron remain pending, not silently recomputed from a stale version.
* `EVENT_TIME` comes from the consumed occurrences. `SERVICE_TIME` comes from the service owner. A delayed external arrival can lead to a batch prepared long after its event timestamp.
* Functional routing/emission manifests are still predeclared upstream (historically trace-derived). This component does not independently generate the full network's outputs, advance arbitrary internal writes, settle OUTPUT candidate spikes, prove replay authenticity under arbitrary forged initial states, or detect deadlock.
* Prepared output pairs are merely candidates. They **must not** be published until the future STATE_COMMIT/OUTPUT transaction owner proves its full obligations.

## Test and acceptance

`python -m pytest -q tests/test_owned_internal_reads_v0.py`

`python -m pytest -q`

Expected on top of the previously validated 1,513 suite tests: 32 new tests, 1,545 in total. A locally reconstructed test environment passed the 32 new tests and 395 combined tests; parts of its architectural models are substitutes, **not** the real fwork repository.

Do not edit frozen SPK Core v0, Network v0, or Compiler v0. Do not commit until the real repository passes and the staged diff is reviewed.

## Next acceptance hurdle

Add the **same owner-controlled** `STATE_COMMIT` and output admission. It must prove causal ordering of P/S read -> EVENT consumption -> Core execution -> state update -> atomic OUTPUT publication, reject stale P/S reads, and verify end-to-end equivalence with independent Network v0.

## Extension S3.7d/3b2b2k/6: historical receipts

The owned read state gains a backward-compatible optional `commits` tuple.
Previously, every `STATE_LOAD` receipt was checked against *current* neuronal
state, which incorrectly invalidated completed reads after an authorized
commit. The extended owner now replays recorded Core commits from the frozen
initial neuronal image and checks each read against its **versioned historical**
state. Reads not yet bound to a committed transition may not use a stale
version. Completed batches are not prepared again.

This is a change to a nonfrozen S3 simulator module. The original 32 tests
remain unmodified and must all pass together with the new commit tests.
