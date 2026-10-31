# SPK S3.7d/24i: Application Runtime Host Contract v0

**Status: CONTRACT PROPOSAL — NOT AN IMPLEMENTED HOST.**

Baseline: `c42ce86` (24h corrected static-audit checkpoint, 2026-10-15).
The reported full checkout has 357 Python files, no detected application host,
no application consumer of 24g, four internal raw-owner importing modules,
and no parse errors. Full-suite baseline: 2,510 passing tests. These are
observations from `fwork`, **not** tests of this proposed contract.

This document decides the smallest application boundary needed to consume the
existing 24g dispatcher. It creates **no host, no external ingress adapter,
no global single-writer guarantee, and no new scheduling clock**. Core v0,
Network v0, Compiler v0, k24b, and 24d–24g remain untouched.

## 1. Decision: first host scope

The first candidate host SHALL be **one cooperative OS process managing one
root epoch for the entire lifetime of its host instance**, with one private
`OwnedRootExecutionDispatcherV0` instance. It is an offline, finite-execution
application boundary; no sockets, HTTP, MQTT, background tasks, network
routing, worker pool, multiprocessing, or persistence is assumed in v0.

A second epoch requires a **new host lifecycle**, never reinstallation of the
same 24g dispatcher. Merely constructing another Python host does not make
it mutually exclusive with the old one; deployment MUST explicitly ensure
that no other authorized host instance owns the same epoch, or document that
this assumption is unverified. At this stage we deliberately **do not claim
process-wide exclusivity**.

This decision addresses the concrete 24h finding: no application host is
identified. It must not be satisfied by adding a class named `Host` which is
never connected to a real consumer. A production-entrypoint claim requires
an identified source of epochs and an actual caller through the host.

## 2. Existing contracts that are normative

- `spk_simulator.owned_shared_event_cycle_v0.OwnedSharedEventCycleStateV0`:
  requires canonical structural consistency of an external/dynamic epoch;
  its seal **does not attest the source** of the initial history.
- `spk_simulator.owned_root_execution_dispatch_v0.OwnedRootExecutionDispatcherV0`:
  `install(shared, *, epoch_id)` installs exactly one fresh epoch. Successful
  installation returns `OwnedRootExecutionViewV0`, not a raw owner.
- `DispatchRequestV0(epoch_id, operation, expected_revision=None,
  max_actions=None)` is canonical. Permitted operations are `SNAPSHOT`,
  `ADVANCE`, `RUN`, `AUDIT`, and `TRACE`. Mutation requires an exact current
  revision; `RUN` also requires a strictly positive bounded `max_actions`.
- `DispatchResultV0` carries the observation projection. Neither revision
  nor `epoch_id` is an authentication capability.
- `OwnedRootCustodyExecutionV0` selects root, zero-tick handoff and terminal
  commit through k24e. Handoff advances custody revision but does **not**
  consume `SERVICE_TIME`; root/terminal successful steps spend exactly one.
- `CLOSED` refuses mutation and allows observation. S commit and its version
  increment are validated by the existing 24d–24g chain; no outputs are
  published in this supported root-commit path.

A future host MUST reuse these public interfaces; it SHALL NOT call k24b,
24d, 24e or 24f directly, manufacture a prepared root, or maintain its own
service counter. Their availability to arbitrary Python code remains a
limitation of cooperative encapsulation, not a security feature.

## 3. Ownership and data-plane boundary

```text
EXPLICITLY SELECTED IN-PROCESS EPOCH PROVIDER  [not yet specified]
    | validated source/provenance responsibility (outside 24g)
    v
HOST ADMISSION  [one epoch / one dispatcher, no reset]
    | OwnedSharedEventCycleStateV0 + matching seal.epoch_id
    v
PRIVATE 24g DISPATCHER
    | DispatchRequestV0 only; observation-only responses
    v
24f -> 24e -> k24b ROOT --handoff--> 24d TERMINAL -> CLOSED
    | one SERVICE_TIME only; handoff costs zero ticks
    v
HOST STATUS / OBSERVATION (no new scheduling clock)
```

An actual host MUST name the epoch provider, its trust boundary and the
consumer that submits commands **before deployment**. A test fixture is not
an epoch provider in production, and importing 24g from a new library is not
application adoption. An in-process trusted provider is acceptable for the
first offline integration test, provided it is named as an **integration
fixture**, never cryptographic authentication.

Only the host owns its dispatcher reference; the consumer receives immutable
observation objects and typed application errors. It SHALL NOT be offered a
root, terminal owner, custody registry, driver or alternate owner selector.
The host and its consumers must cooperate and run in the declared process
scope. Python reflection and direct imports cannot be prohibited by this
contract alone.

## 4. Host lifecycle (control plane, not SERVICE_TIME)

| Host state | Allowed transition | Meaning |
| --- | --- | --- |
| `NEW` | `ADMIT` -> `ACTIVE` | One trusted-for-scope, fresh epoch accepted; 24g installed exactly once. |
| `NEW` | failed admission -> `NEW` | Rejection before installation; no service or published dispatcher. |
| `ACTIVE` | read-only observe -> `ACTIVE` | `SNAPSHOT`, `AUDIT`, `TRACE`. |
| `ACTIVE` | `ADVANCE` or bounded `RUN` -> `ACTIVE` | Delegate to 24g, use current revision; incomplete is not success. |
| `ACTIVE` | observed `CLOSED` -> `CLOSED` | Receipt is present and output-free; no future mutation. |
| `ACTIVE` | execution/host error -> `FAILED` | Fail-stop mutating admission; no claim of rollback of prior steps. |
| `CLOSED` | read-only observe -> `CLOSED` | No reset, resume, or second install. |
| `FAILED` | diagnostic observe -> `FAILED` | Best-effort read-only inspection; no automatic retry or reinstallation. |

No `STOPPED -> ACTIVE` recovery is provided by v0. A shutdown while `ACTIVE`
means **incomplete**, not committed; shutdown never synthesizes a terminal
receipt. `CLOSED` means the underlying dispatcher reports closed, not merely
that a host loop exhausted a time/action limit. Control-plane states are not
new neuron states and their transitions never spend `SERVICE_TIME`.

`FAILED` is a host-level policy decision, not an existing 24g enum. Once an
accepted bounded `RUN` has partially progressed, a later exception may leave
valid prior changes. The host MUST inspect/report the last authoritative
24g revision without claiming that the entire call rolled back. Failed
observation may itself be unavailable; this does not authorize a fresh owner.

## 5. Command and observation policy

1. A host command MUST be one of the existing canonical 24g operations and
   MUST carry the installed `epoch_id`. An unknown operation is rejected,
   not forwarded to a raw owner.
2. `ADVANCE` and `RUN` MUST use the consumer-supplied `expected_revision`,
   with the strict 24g type checks. Host-side automatic stale-revision retry
   or hidden revision bump is forbidden.
3. `RUN` MUST have a finite explicit `max_actions` budget. Exhausting the
   budget with `completed=False` is a normal **incomplete** result, never a
   success receipt or automatic continuation.
4. Read-only `SNAPSHOT`, `AUDIT`, `TRACE` do not accept a revision or budget.
   `TRACE` is replayable evidence relative to the trusted initial snapshot,
   not proof of source legitimacy or a tamper-proof external ledger.
5. On `CLOSED`, only read-only operations can pass. In `FAILED`, the host
   policy also forbids subsequent mutation, regardless of what 24g would
   technically accept.
6. If a host exposes a transport later, translating untrusted payloads into
   `DispatchRequestV0` and authenticating callers become separate security
   obligations. No transport is part of this v0 contract.

## 6. Error, resource and completion semantics

- **Admission rejection:** before successful `install`, no published epoch,
  and no attributed service ticks. No misleading installed/committed status.
- **Stale revision / wrong epoch / invalid request:** fail closed, preserving
  the last accepted state; do not transform rejection into implicit refresh,
  retry or owner selection.
- **Partial `RUN` failure:** accepted substeps may remain valid; the host goes
  fail-stop for mutation and preserves diagnostics as available. No whole-run
  rollback promise; no silent new epoch.
- **Service or resource failure:** expose the failure and its origin when
  available; never fabricate a successful `STATE_COMMIT` or discard a pending
  output as if it were committed. Out-of-scope output-bearing Core executions
  are rejected by the existing chain.
- **Completion:** only a `CLOSED` observation with a genuine output-free
  `commit_receipt` is success for this finite path; it must not be inferred
  from reaching `max_actions`, a status flag supplied by the caller, or a
  host-controlled timeout.
- **Crash/power loss:** no durability, restart replay, process fence or
  persistent atomicity is claimed. A new process cannot reconstruct trusted
  authority merely from 24g `TRACE` or an `epoch_id` string.

## 7. Required integration tests before claiming a concrete host

| ID | Gate | Expected negative or positive evidence |
| --- | --- | --- |
| H01 | Real application entrypoint | Identify actual executable/consumer and installed provider; 24h scanner sees a real 24g consumer, not an import alone. |
| H02 | Admission | Fresh sealed epoch accepted; wrong type/mismatch rejected without leaking dispatcher. |
| H03 | Lifecycle | Duplicate admit/reset rejected, including after CLOSED or FAILED. |
| H04 | Single writer | Concurrent commands with same revision produce only one accepted mutation; no transparent retry. |
| H05 | Bounded run | Incomplete RUN remains incomplete; resume requires a new, exact revision. |
| H06 | Root/terminal integration | Real fixture reaches exactly one handoff and one output-free S commit; zero handoff tick; version +1. |
| H07 | Failure | Rejection/partial execution never reports success or rolls back accepted work in its description. |
| H08 | Shutdown | Incomplete shutdown is not success; CLOSED is read-only; no automatic recovery after host failure. |
| H09 | Boundary | Application traffic cannot choose raw owners through exposed host API; direct legacy imports are separately listed as out of scope. |
| H10 | Source/provenance | Named provider and verifiable trust assumptions recorded; seal structural validity is not marketed as authentication. |
| H11 | Deployment scope | Single-process, single-epoch authority assertion is reviewed against actual launcher; no multi-process uniqueness claim. |
| H12 | Regression | Core/Network/Compiler and 24b–24g unchanged; full `pytest` and `git diff --check` pass on `fwork`. |

H01, H10 and H11 are **architectural blockers**, not items that can be
replaced by mock-heavy tests. The 24h static audit is an evidence inventory,
not a proof of dynamic mandatory dispatch. A concrete host's gate must
report both static entrypoint evidence and a live end-to-end request flow.

## 8. Implementation boundary for 24j

**Proposed implementation:** one process-local, fail-stop host using one 24g
dispatcher and an explicitly named, trusted-for-scope epoch provider. It may
be offered as a thin in-process integration API first, but SHALL NOT be
called a deployed application host until a real entrypoint and consumer are
wired. Introduce no second owner, scheduler, persistence, networking, leases,
or consensus. Do not alter frozen or previously validated modules.

Before coding 24j, identify the real epoch creation path and consumer entry
point, or explicitly label the result **reference integration harness**.
If no actual producer/consumer exists, 24j may validate an integration harness
but the application-adoption gate MUST remain `OPEN`.

## 9. Checkpoint policy

24i is a design and acceptance-contract checkpoint. It intentionally adds
**zero** tests and **zero** executable modules. Do not increment regression
test counts, infer application adoption, or promote the full Simulator stage
from a document alone. It may be committed separately after review and
`git diff --check`. The last verified full-suite total at this baseline is
2,510, not a freshly executed suite in this environment.

The five-phase baseline stays S1=100%, S2=100%, S3=60%, S4=0%, S5=0%:
**52% total** using a straight five-phase average. Blocker: no real
consumer/provider host identified; next activity: concrete 24j integration
within the declared runtime boundary, with explicit admission and failure
semantics and a separate deployment-adoption gate.
