# SPK S3.7d/24d: Terminal Commit Handoff Validation v0

Status: **PASS, scoped to deterministic terminal STATE_COMMIT replay and local state/version atomicity.**

Validation on `fwork` (2026-10-15): new terminal suite **23 passed**,
combined Owned Root + terminal suite **58 passed**, repository suite
**2367 passed in 9.28 s**. The preceding full checkpoint contained 2344
tests, so the delta is +23 tests, with no regressions detected.
These execution results were reported from the repository; this document
records them without claiming an independent run in the source-bundle review
environment.

**Excluded from PASS:** unique handoff across independent owners/processes,
revocation of retained k24b references, cryptographic snapshot provenance,
and persistence after crash. The test showing that two independent handoffs
remain possible is intentionally passing evidence of that limitation.
These are explicit blockers for any broader *exclusive authority* claim.

## Contract and authority boundary

`spk_simulator.owned_root_terminal_commit_v0` is a separate, narrowly scoped
owner. It does not modify or invoke the k24b `advance_owned_root_single_clock_v0`
implementation. The original `OwnedRootSingleClockStateV0` is retained as the
**unchanged historical input**; the terminal owner has distinct current
`ServiceQuantumStateV0`, current `VersionedNeuronImageV0`, and an append-only
sequence of `TerminalCommitQuantumV0` execution records.

This version supports **one** serialized, physically completed external root
batch per epoch and exactly one `STATE_COMMIT`. It is **not** a general-purpose
neuronal batch scheduler.

```text
k24b snapshot: P/S actual receipts + consumed EVENT tombstone + Core prepare
    | (all noncommit requests confirmed, no pending/partial work,
    |  all sealed external events consumed, no Core candidate output)
    v
Terminal owner (only STATE_COMMIT may spend service)
    | quantum(t): actual service slices
    | quantum(t+1...): finish, only subsequent-boundary confirmation
    v
S image version 0 -> 1 AND STATE_COMMIT confirmation (one immutable successor)
```

The terminal module will not call k24b to spend service. It invokes the common
`advance_service_quantum_v0` exactly once for each new terminal boundary.
Dispatch is `(<commit_id>,)` until service exhaustion, then empty while the
finish awaits confirmation. No other request is dispatched; partial work for
any noncommit request is rejected.

## Handoff gate

`handoff_owned_root_terminal_commit_v0(root)` revalidates the k24b root,
serialized dependency graph, physical witness coverage and frozen Core
preparation. The handoff is rejected if any of the following is true:

- multiple batches or additional registered activities are present;
- `STATE_COMMIT` was already dispatched, finished or confirmed;
- a P/S/BATCH request is unconfirmed, or a partial/pending service exists;
- any sealed external arrival remains resident or unconsumed;
- exactly one matching preparation and physical input witness do not exist;
- Core's candidate output tuple is nonempty.

The old root's `image` is never rewritten: its validated P/S history refers
to the state version actually read at that boundary. The new S image lives
exclusively in the terminal state, avoiding the false retroactive rewriting
of historical STATE_LOAD receipts.

## Replay and evidence

A terminal state is only accepted if replaying **every** terminal quantum,
starting from the retained root's `ServiceQuantumStateV0` and uncommitted S
image, yields exactly its declared service state, image and evidence. This
replay recomputes deterministic service slices, request completion and later
confirmation. At commit, it independently recomputes the frozen Core result,
checks that there are no candidate emissions, then constructs the service
confirmation and versioned write as one immutable successor.

A truncated, duplicated, reordered or altered terminal history is rejected;
so are unsupported service requests, wrong `SERVICE_TIME` slices, premature
confirmation, fabricated receipts and claimed version changes with no matching
service quantum.

The final quantum contains the confirmation plus the S receipt. The prior
quantum that exhausted the work carries no S receipt, even if the service
requirement was one unit. The finish is visible at the **next** boundary.

## Safety limitations and deliberately unproven claims

1. **Snapshot trust:** k24b's installation and historical service state are
   assumed valid. Terminal replay authenticates *relative consistency with
   that handoff*, not the origin of the root history. There is no cryptographic
   trust anchor.
2. **Exclusivity:** Python immutable dataclasses cannot revoke other live
   references to the k24b root; independently created terminal owners may
   fork from the same historical snapshot. The integration orchestrator must
   transfer authority exactly once and stop advancing the old owner. This
   cannot be proven by the present pure-function API. A genuine one-time
   transferable capability or a persisted authoritative owner registry is a
   separate design decision.
3. **Atomicity:** S and service confirmation are created in one immutable
   result, with no externally observable partial successor. Host crash
   persistence and transactional storage durability are not provided.
4. **Outputs:** Any actual candidate emission is rejected. No OUTPUT,
   notification, network routing or action is emitted by this owner.
5. **Coverage:** Only one root batch / one commit, no next-cycle batching,
   learning, rollback of historical k24b effects, retention compaction or
   distributed ownership.
6. **Resource scheduler:** The existing service-quantum computation, including
   its scheduling and causal-frontier policies, remains authoritative. Tests
   cannot prove the general soundness of those frozen components.

## Validation matrix

| Claim | Test(s) | Expected result |
| --- | --- | --- |
| Real P/S, consumed EVENT and unique Core prepare | `test_handoff_witnessed_closed_root_and_output_free`, `test_missing_preparation_rejected`, `test_no_handoff_before_core_prepare` | accept valid; reject missing |
| Commit after service exhaustion only | `test_full_service_commit_and_separate_later_confirmation` | finish before S receipt |
| Multi-tick, per-PE service | `test_multiquantum_partial_service` | exact units, no intermediate version |
| Terminal-only dispatch | `test_full_service_commit_and_separate_later_confirmation` | all terminal slices commit ID |
| No output | `test_output_bearing_transition_is_rejected` | fail closed |
| Replay deterministic | `test_deterministic_replay` | same immutable successor |
| Altered service slices and tick | `test_mutated_service_slices_rejected`, `test_mutated_terminal_tick_rejected` | reject |
| Fabricated finish/confirmation | `test_fabricated_terminal_effect_rejected` | reject |
| Dropped/duplicate/reordered history | `test_dropped_quantum_rejected`, `test_reordered_or_duplicated_quantum_rejected` | reject |
| Claimed clock/state/version/receipt | `test_forged_service_clock_rejected`, `test_forged_state_version_rejected`, `test_forged_receipt_rejected` | reject |
| Idempotent post-terminal behavior | `test_cannot_reenter_terminal_owner_after_commit` | refuse another advance |
| No mutation of historical owner | `test_full_service_commit_and_separate_later_confirmation` | original image/storage unchanged |
| Global handoff uniqueness / revocation | `test_two_independent_handoffs_remain_possible_without_external_registry` | **not established; demonstrates forkable authority** |
| Host crash durability | **not implemented** | not claimed |

## Execution on fwork

Overlay **only** the three new files from the patch archive onto the
unchanged repository (do not replace k24b, Core, Network or Compiler).

```bash
python -m pytest -q tests/test_owned_root_terminal_commit_v0.py
python -m pytest -q tests/test_owned_root_single_clock_v0.py tests/test_owned_root_terminal_commit_v0.py
python -m pytest -q
git diff --check
git status --short
```

The supplied source bundle omitted the `spk_architecture`, `spk_network`,
`spk_compiler` and `spk_core` runtime packages. As a result, in this editing
environment we can syntax-compile the patch but **cannot** claim a passing
integration/full pytest run. This status must only be promoted after the
real fwork gate passes.


## 24d release-gate disposition

- **Promoted within the stated scope:** consumed sealed EVENT inputs,
  actual P/S service receipts, unique witnessed Core preparation,
  terminal-only `STATE_COMMIT` service, separate later-boundary
  confirmation, exact deterministic quantum replay and local S/version
  commit coherence.
- **Not promoted:** single-use authority across independently created
  terminal owners or another process; unchanged k24b cannot revoke
  previously retained root snapshots. `frozenset`, a dataclass flag or a
  replay hash would not constitute a non-duplicable capability.
- **24e candidate:** specify a trusted single-writer custody boundary for
  the handoff before implementing it. Require a clear trust domain,
  admission authority, exactly-once transfer, duplicate/retry behavior,
  failure semantics and restart limitations. Do not expand the frozen
  k24b surface to accommodate the new boundary.

The 24d PASS must not be interpreted as a proof of global ownership or
crash-safe transactional durability.
