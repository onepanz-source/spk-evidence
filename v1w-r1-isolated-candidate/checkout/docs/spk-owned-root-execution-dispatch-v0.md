# SPK S3.7d/24g: Owned Root Execution Dispatch Boundary v0

Status: **INTEGRATION PASS (single-epoch cooperating boundary only)**.
The targeted and full `pytest` suites passed on `fwork` on 2026-10-15.
This is neither a global dispatcher installation nor a release tag.

## 1. Scope and source audit

The 24d source bundle was inspected alongside the subsequently supplied 24d,
24e, and 24f patch modules. `spk_simulator` contains several older, separate
functional runners (including bounded backpressure and autonomous storage),
but the supplied repository contains **no single authoritative application host
entrypoint** through which all simulator consumers already run. Hence this
change cannot truthfully claim to retrofit those paths or replace them.

This component introduces an **opt-in, one-epoch cooperating dispatch boundary**
that can be installed by a future host. It delegates all execution to the
existing 24f `OwnedRootCustodyExecutionV0`, which exclusively selects k24e
custody operations. It does not change k24b, k24d, k24e, k24f or Core, Network,
Compiler. This is a control-plane boundary, not another service scheduler.

## 2. Authority graph

```text
trusted caller supplies fresh sealed OwnedSharedEventCycleStateV0
                       |
                       | install(shared, epoch_id=actual seal.epoch_id), once
                       v
        OwnedRootExecutionDispatcherV0
          |          |             |
          |          +-- read-only SNAPSHOT, AUDIT, TRACE
          |
          +-- typed ADVANCE / bounded RUN at current revision only
                       |
                       v
         OwnedRootCustodyExecutionV0 (24f)
                       |
                       v
   k24e registry -> k24b ROOT -> HANDOFF -> k24d TERMINAL -> CLOSED
```

Only one epoch may ever be installed in a dispatcher object; there is no reset,
replacement, or second installation after CLOSED. The epoch ID is checked
against the sealed input, and is checked again on every request. The ID is
**not** an authentication credential, authorization token, or unforgeable
capability. Other dispatcher instances can install the same trusted epoch.

The 24f runner is constructed before its reference is published, so failed
initialization does not consume installation. All public calls are serialized
under one dispatcher lock. The driver lock and registry lock provide nested
cooperative single-writer serialization, without introducing a new logical
clock. The only revision and SERVICE_TIME are those already owned by 24f.

## 3. Public protocol

`OwnedRootExecutionDispatcherV0` offers:

- `install(shared, epoch_id=...)`: one-shot install from an untouched, sealed
  EVENT/P/S epoch; returns an observation-only `OwnedRootExecutionViewV0`.
- `dispatch(DispatchRequestV0(...))`: exactly one of `SNAPSHOT`, `ADVANCE`,
  `RUN`, `AUDIT`, `TRACE`. Both input and output are canonical, frozen data
  classes. No raw root, registry, terminal owner, or 24f runner is returned.

For `ADVANCE`, `expected_revision` is mandatory and `max_actions` forbidden.
For `RUN`, both `expected_revision` and positive `max_actions` are mandatory.
For read-only requests, neither is allowed. `bool`, float, `None`, strings
masquerading as integers, malformed operations, and forged dataclasses are
rejected before mutation. A request for another epoch fails before touching
the runner. A stale revision fails before spending SERVICE_TIME.

During `ROOT_OWNED`, 24f runs k24b until Core preparation; its prepared root
must attempt HANDOFF and cannot fall back to k24b if handoff fails. During
`COMMIT_OWNED`, only k24d advances service. HANDOFF consumes one custody
revision but zero SERVICE_TIME. Completion confirms S/version exactly once
with no output publication. After CLOSED, the dispatcher permits only
read-only `SNAPSHOT`, `AUDIT`, and `TRACE`; even an otherwise harmless `RUN`
request is rejected, rather than being advertised as a new execution.

`RUN` is bounded, may return incomplete with a resumable revision, and has no
whole-run rollback. Earlier successful actions remain valid if a later action
fails. This contract does not claim host crash safety or persistent state.

## 4. Guarantees and limitations

**Enforced for a single dispatcher instance and cooperating callers**:

- no caller-selected k24b/k24d owner or arbitrary injected owner state;
- one fresh root registration, and no reinstallation after completion;
- strictly typed, epoch-bound, revision-checked mutating requests;
- serialized requests; one accepted mutation for a given revision;
- no root advancement after HANDOFF through this boundary;
- no terminal advancement before HANDOFF through this boundary;
- no second scheduler clock and no fabricated commit acknowledgement;
- read-only replay/audit and trace observation after closure.

**Not enforced**:

- existing code importing and calling old functional runners directly;
- process-wide, cross-process, cross-host, or cross-dispatcher uniqueness;
- revocation of retained immutable roots, unforgeable capabilities, OS-level
  privilege isolation, cryptographic authentication, or recovery after crash;
- any guarantee that the actual deployment's top-level host adopts this API;
- arbitrary Python reflection/access to private `_runner`, or protection
  against an intentionally malicious in-process caller;
- output-bearing Core executions, multi-neuron general-network scheduling,
  and dynamic route emission.

An explicit test demonstrates that two independent dispatcher objects can
complete separate histories from the same trusted epoch. This is a declared
architecture limitation, not proof of global exclusion.

## 5. Tests and acceptance

`tests/test_owned_root_execution_dispatch_v0.py` exercises:

- fresh installation; mismatched/invalid epoch and type; duplicate admission;
- valid/rejected command schemas including forged dataclass input;
- single SERVICE_TIME progression, zero-service handoff, and S/version commit;
- P/S/Core physical evidence inherited through the real k24f finite fixture;
- historical trace, audit, and immutable observation projection;
- bounded continuation, stale/CLOSED requests, concurrency CAS races;
- initialization/owner/terminal/handoff fault injection;
- independent-instantiation non-exclusivity.

Commands to run on `fwork` after extracting **only new files**:

```bash
python -m pytest -q tests/test_owned_root_execution_dispatch_v0.py
python -m pytest -q \
  tests/test_owned_root_single_clock_v0.py \
  tests/test_owned_root_terminal_commit_v0.py \
  tests/test_owned_root_authority_custody_v0.py \
  tests/test_owned_root_custody_execution_v0.py \
  tests/test_owned_root_execution_dispatch_v0.py
python -m pytest -q

git diff --check
git status --short
```

The source bundle available outside `fwork` lacks frozen `spk_architecture`,
`spk_core`, and `spk_network`. Static checks and any isolated mock checks are
**not** a substitute for the full integration gate.

**Promotion criterion**: targeted suites and full suite pass; only three 24g
files staged; documented limited boundary retained. No commit or tag is
included in the distributed patch.

## 6. Recorded fwork acceptance (2026-10-15)

The repository owner ran the new 24g test file, the integrated 24b/24d/24e/24f/24g
regression, and the full suite on the complete `fwork` checkout.

| Gate | Observed result |
| --- | --- |
| `tests/test_owned_root_execution_dispatch_v0.py` | **51 passed**, 0.33s |
| 24b + 24d + 24e + 24f + 24g focused suites | **178 passed**, 0.67s |
| `python -m pytest -q` | **2487 passed**, 9.64s |
| Increase from the 24f 2436-test suite | **+51 tests; no failures reported** |
| `git diff --check` | No issues reported |

The reported worktree contained three new 24g files plus these unrelated
untracked files, which must be excluded from the checkpoint:

- `search/core_temporal_depth5_v1.py`
- `search/core_temporal_quotient_alignment_v0.py`
- `spk_24d_collect.py`

**Gate result: PASS in the declared local cooperating domain.** The successful
tests provide evidence for one dispatcher instance, one installed epoch,
revision-based dispatch and the existing custody/commit chain. They do not
prove that every application caller uses the dispatcher, or that separately
constructed dispatcher instances are mutually excluded. The explicit
independent-dispatcher test demonstrates the latter limitation. Cross-process
fencing, host-wide adoption, crash durability, and cryptographic authentication
are not covered.

**Next integration action:** inventory actual application ingress/dispatch
callers and define an explicit host adoption contract, rather than adding a
further protective wrapper without evidence that any application uses it.
Before committing, stage and inspect *only* the three 24g files.
