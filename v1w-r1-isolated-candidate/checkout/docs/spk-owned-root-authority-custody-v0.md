# SPK S3.7d/24e: Owned Root Authority Custody v0

Status: **PASS (bounded to process-local, cooperating single-writer custody)**.
The implementation, tests, and documentation introduce a new wrapper without
changing k24b, k24d, Core, Network, or Compiler. This status does **not**
certify exclusive authority across independent registries or processes.

## Goal and trust boundary

Prevent duplicate service progress and duplicate terminal handoff **inside one
in-memory, process-local, single-writer custody registry**. A registry is
installed once, with one historical `OwnedRootSingleClockStateV0` from the
trusted caller. All authorized operations must go through that registry.

**This is not global linear authority.** A raw historical k24b snapshot can
still be advanced by callers who bypass the registry, and two separate
registry instances (or separate processes) can each install the same root.
Immutable snapshots are values, not revocable capabilities. The registry is a
cooperating controller and not a cryptographic or OS-enforced security domain.

## Owner states

```text
new registry (uninstalled)
    | install(k24b root), exactly once
    v
ROOT_OWNED             advance_root(rev) -> ROOT_OWNED, rev+1, one service tick
    | handoff(rev) after k24d gate
    | no SERVICE_TIME consumed; rev+1
    v
COMMIT_OWNED           advance_terminal(rev) -> COMMIT_OWNED, rev+1, one tick
    | terminal service confirmation and S/version write
    v
CLOSED                 all further advancement and handoffs rejected
```

Handoff reuses `handoff_owned_root_terminal_commit_v0`, which checks the
historical P/S physical read confirmations, consumed EVENT tombstones,
Core preparation and output-free result. During ROOT_OWNED, only
`advance_owned_root_single_clock_v0` is called. During COMMIT_OWNED, only
`advance_owned_root_terminal_commit_v0` is called. A custody handoff does not
invoke the service quantum; no second clock is introduced. The last terminal
step makes S/version visible at the same later boundary as the k24d receipt.

Each accepted method takes `expected_revision`, requiring exact integer
identity with the registry's current revision. Revision is a **control-plane
CAS counter**, not a second time dimension and not a bearer security token.
A duplicate/retried request using the old revision raises
`CustodyStaleRevisionV0` without a new step. Repeating an operation using the
new current revision but the wrong phase raises `CustodyPhaseErrorV0`.
Nothing is silently treated as a successful idempotent retry: a rejected
retry means the client must read `snapshot()` and reconcile the outcome.

The implementation uses one `RLock` to serialize installation, state reads,
root steps, handoffs, terminal steps and audit verification within the registry
object. Computation is performed before publishing its successor. Exceptions
from the owner or invalid handoff therefore do not advance the registry's
revision, service state or log. The registry cannot be reinstalled after
CLOSED, and does not implement rewind or force-reset.

## Trace and reconstruction

Each successful authority operation appends one immutable `CustodyRecordV0`:

- monotonically increasing revision;
- operation kind (`ROOT_STEP`, `HANDOFF`, `TERMINAL_STEP`);
- resulting authority phase;
- resulting **existing** `next_service_tick` (not a new clock).

`replay_custody_trace_v0(initial_root, trace)` rebuilds all steps in order
using the actual k24b and k24d functions, checking every declared revision,
phase and SERVICE_TIME boundary. `registry.verify()` replays from the
installation root and compares the complete reconstructed owner states and
trace with the stored registry state. Duplicate, reordered, missing, forged
or illegal authority operations cannot pass a *claimed unchanged final
snapshot* through this verification. A shorter well-formed trace correctly
reconstructs a different (earlier) state: the trace itself is not an
append-only externally authenticated ledger.

Important distinction: deterministic replay checks internal consistency
relative to the **trusted installation snapshot**. It does not authenticate
the requester's permission to submit an operation, the original installation
root, or whether the registry was bypassed. Any party with unrestricted
in-process Python execution can create another registry and/or directly
invoke pure owner functions.

## Guarantees and exclusions

| Property | Inside a single cooperating registry | Across independent registries/processes |
| --- | --- | --- |
| Single mutation linearization point | Lock and CAS | Not guaranteed |
| Duplicate handoff | Rejected | Fork still possible |
| k24b after transfer | Rejected through registry API | Raw k24b call not revoked |
| Duplicate terminal advancement | Stale revision rejected | Not guaranteed |
| One `SERVICE_TIME` advancement per accepted service step | Checked against k24b/k24d | Separate clocks can fork |
| Handoff advances no service tick | Checked | Does not authenticate provenance |
| S/version commit | Delegated to replay-audited k24d | No host crash durability |
| Crash recovery | None | Requires persistent authoritative protocol |
| Authorization/security boundary | Trusted cooperating code | No cryptographic/OS authority |

A future durable or distributed owner contract requires a genuinely shared
linearization point, a persistent epoch/lease/fencing token scheme, and an
explicitly defined crash-recovery and external-effect policy. Simply placing a
UUID, hash, boolean, frozen dataclass or in-memory singleton in the snapshot
would not establish those properties.

## Test matrix

| Gate | Tests in `tests/test_owned_root_authority_custody_v0.py` |
| --- | --- |
| Once-only install, no reset | `test_cannot_install_twice_even_same_root_or_equal_clone`, `test_closed_registry_refuses_any_more_operations` |
| Valid and rejected handoff | `test_handoff_does_not_advance_service_clock`, `test_failure_to_handoff_unprepared_root_preserves_custody`, `test_output_bearing_handoff_fails_without_consuming_authority` |
| Wrong owner / stale retries | `test_root_service_forbidden_after_transfer_even_with_current_revision`, `test_terminal_service_forbidden_before_transfer`, `test_duplicate_handoff_rejected_without_effect`, `test_duplicate_terminal_step_rejected_without_double_spend` |
| Atomic state/version at final confirmation | `test_terminal_quantum_and_final_close`, `test_full_installation_to_terminal_commit_using_one_registry` |
| One root clock / real k24b API | `test_root_service_advances_using_exact_k24b_api`, `test_stale_root_revision_refuses_service` |
| Failure before successor publication | `test_injected_handoff_failure_is_atomic`, `test_injected_terminal_failure_is_atomic`, `test_injected_root_failure_is_atomic` |
| Concurrent callers | `test_concurrent_handoff_same_revision_has_exactly_one_winner` |
| Reconstructed trace against forgery | `test_trace_forged_revision_rejected`, `test_trace_forged_clock_rejected`, `test_trace_forged_phase_rejected`, `test_trace_reordered_and_duplicated_handoff_rejected`, `test_trace_missing_terminal_step_does_not_support_closed_claim` |
| Explicit limits | `test_snapshot_is_immutable_but_not_a_revoke_capability`, `test_separate_registry_instances_remain_an_explicit_fork_risk` |

## Acceptance on fwork

```bash
python -m pytest -q tests/test_owned_root_authority_custody_v0.py
python -m pytest -q \
  tests/test_owned_root_single_clock_v0.py \
  tests/test_owned_root_terminal_commit_v0.py \
  tests/test_owned_root_authority_custody_v0.py
python -m pytest -q

git diff --check
git status --short
```

### Recorded gate result on `fwork` (2026-10-15)

The repository owner executed and supplied these results:

| Check | Actual result |
| --- | --- |
| `tests/test_owned_root_authority_custody_v0.py` | **32 passed** in 0.30s |
| Combined `owned_root_single_clock`, `owned_root_terminal_commit`, and `owned_root_authority_custody` | **90 passed** in 0.39s |
| Full `python -m pytest -q` | **2399 passed** in 9.43s |
| Delta versus 24d full regression (2367) | **+32 tests; no reported regressions** |

This is an integration **PASS inside the documented trust boundary**, not
proof of global non-forking, crash recovery, durable authority, or isolation
from other independently constructed registries.

The supplied source bundle used for development lacks `spk_architecture`,
`spk_core`, `spk_network`, and `spk_compiler`, so the full run was performed
on `fwork`, not on the development bundle. The verification of the staged
patch with `git diff --cached --check` remains required before committing.

## Promotion criterion

The reported PASS promotes 24e **only as process-local cooperating
single-writer custody**. It does not resolve independent forked authorities,
external side effects, crash durability or multi-process operation. Future
24f work should be scoped according to the first actual consumer's trust
boundary, not prematurely introduce a distributed consensus system.
