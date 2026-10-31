# SPK S3.7d/24f: Owned Root Custody Execution v0

Status: **INTEGRATION PASS (cooperating entrypoint only)**. Focused and full
regression suites ran successfully on `fwork` on 2026-10-15. This acceptance
does not make the entrypoint mandatory for other simulator consumers.

## Objective

Offer the first **opt-in, custody-enforced, cooperating application entrypoint**
for a single sealed root epoch. All actions originating in this entrypoint must
pass through the **same** k24e `OwnedRootAuthorityRegistryV0` rather than
leaving the application to choose between independent k24b and k24d calls.

This does **not** retrofit the rest of the simulator or forbid external callers
from directly importing pure owner functions. The entrypoint is an integrated
path, not a process-wide mandatory scheduler or OS-enforced security boundary.
Its `__slots__` and private attributes are not security capabilities.

## Entry / observation boundary

`OwnedRootCustodyExecutionV0(shared)` accepts one untouched
`OwnedSharedEventCycleStateV0` from the existing sealed external batch. It
calls `initialize_owned_root_single_clock_v0(shared)` and creates its own
k24e registry. It does not accept an already-prepared k24b state or a
precommitted k24d result. It has no restart or reset.

Public methods are:

| Method | Contract |
| --- | --- |
| `snapshot()` | Frozen minimal observation: custody phase, revision, existing next SERVICE_TIME, neuron versions and optional final commit receipt. No raw root, terminal or registry in the observation. |
| `advance(expected_revision=rev)` | One custody action, selected internally. Caller cannot choose k24b/handoff/k24d. Returns action, revision, service delta and safe observation. |
| `run(expected_revision=rev, max_actions=N)` | Bounded sequence under one driver lock; returns each accepted action and an explicit `completed` bit. Budget exhaustion does not claim completion. |
| `audit()` | k24e replay verification of the entire accepted custody trace from the installation root; returns only the observation. |
| `trace()` | Immutable custody action records, replayable relative to the trusted initial root. Not an authenticated external ledger. |

Exact-int revisions are required for optimistic admission. Bad/stale revisions
are rejected before any owner call; duplicates therefore cannot cause a
second accepted operation through the entrypoint. The driver serializes calls
at the driver boundary and k24e independently serializes its custody actions.

## Automatic state machine

```text
fresh sealed EVENT/P/S epoch
       | initialize k24b; install one k24e registry
       v
ROOT_OWNED -- advance root one SERVICE_TIME --> ROOT_OWNED
       | if Core prepared: try validated handoff
       | (fail closed; no fallback into root)
       | exactly one custody revision; zero SERVICE_TIME
       v
COMMIT_OWNED -- advance terminal one SERVICE_TIME --> COMMIT_OWNED
       | final k24d confirmation of S at later boundary
       v
CLOSED
```

`advance` does not add a time dimension: it reuses the SERVICE_TIME tick
provided by k24b/k24d, with exactly +1 for a root or terminal service action
and 0 for handoff. The custody revision increments once for **each accepted
authority action**, including handoff; it is control metadata, not a clock.

A prepared root is deliberately a strict boundary. If the k24d admission
checks reject incomplete witnesses, unfinished service, or output-bearing
Core results, the operation is rejected without falling back to k24b and
without publishing a new accepted custody revision. The restricted path does
not publish OUTPUT, emit spikes, send notifications or trigger physical effects.

Only the final k24d confirmation exposes the S/version increment (0 -> 1).
The public observation offers the underlying k24d receipt, not a fabricated
or prematurely asserted commit result.

## Bounded execution and failure semantics

`run(max_actions=N)` is not an unbounded `while` loop: callers explicitly
supply a positive integer budget of accepted authority actions, including the
zero-service handoff. If exhausted before CLOSED, it returns an **incomplete**
result with the new revision; a subsequent run may resume by presenting the
current revision. `run` on CLOSED with the current revision returns zero steps
and `completed=True`; `advance` on CLOSED rejects.

If an owner raises during a run, already accepted earlier actions remain
recorded. The failing action has no accepted successor under k24e's exception
contract; this is not whole-run rollback or host-crash atomicity.

`audit()` checks deterministic consistency with the initial trusted snapshot.
It does not provide signature verification, authentication of the initial
snapshot, external immutability or independent durability.

## Enforcement and explicit non-guarantees

**Guaranteed for cooperating clients using only this entrypoint:**

- no caller-controlled choice of raw owner service API;
- no post-handoff root action through this entrypoint;
- no pre-handoff terminal action through this entrypoint;
- no duplicate action accepted at an old control revision;
- one zero-service handoff, then terminal-only SERVICE_TIME;
- final S/version publication only when k24d confirms it;
- validated history through the k24e custody registry.

**Not guaranteed:**

- other existing simulator entrypoints delegate to this driver;
- code with Python execution privileges cannot obtain `_registry`, import
  k24b directly, duplicate the trusted installation root or create another
  runner from the same shared epoch;
- global single writer across instances, processes or hosts;
- crash durability, restart/recovery, persistent fencing, authorization, or
  output-bearing Core transitions;
- long-term liveness if the Core never prepares or an owner fails.

Making this execution interface mandatory for *all* real simulator clients
requires a separately specified dispatch authority or integration with the
actual top-level simulator host. Neither is present in this source bundle.

## Tests and promotion gate

`tests/test_owned_root_custody_execution_v0.py` covers fresh initialization,
automatic root-to-terminal flow, zero-service handoff, output-free receipt,
version visibility, CAS stale/invalid inputs, bounded continuation, concurrent
callers, failure injection in each owner, refusal of output-bearing batches,
observer non-exposure of raw owners, and custody trace replay audit.

On `fwork`:

```bash
python -m pytest -q tests/test_owned_root_custody_execution_v0.py
python -m pytest -q \
  tests/test_owned_root_single_clock_v0.py \
  tests/test_owned_root_terminal_commit_v0.py \
  tests/test_owned_root_authority_custody_v0.py \
  tests/test_owned_root_custody_execution_v0.py
python -m pytest -q

git diff --check
git status --short
```

Promotion requires all tests to pass without modifications to frozen k24b,
Core, Network, Compiler or the existing k24d and k24e implementations. No
Git commit or release tag is included in this patch.

## Recorded fwork acceptance (2026-10-15)

Results supplied by the repository owner after installing the three-file 24f
patch:

| Test set | Observed result |
| --- | --- |
| `tests/test_owned_root_custody_execution_v0.py` | **37 passed** in 0.34s |
| `owned_root_single_clock`, `owned_root_terminal_commit`, `owned_root_authority_custody`, `owned_root_custody_execution` | **127 passed** in 0.55s |
| Full `python -m pytest -q` | **2436 passed** in 9.58s |
| Delta versus the last full 24e checkpoint (2399) | **+37 tests, no reported regressions** |

The supplied `git status --short` shows only the three new 24f files plus
`search/core_temporal_depth5_v1.py`,
`search/core_temporal_quotient_alignment_v0.py` and `spk_24d_collect.py`
as untracked. The latter three are not part of this checkpoint.

**Gate disposition: PASS**, solely for the opt-in single-root, single-registry
execution entrypoint and the contracts exercised by its tests. The results
do **not** prove that every other simulator dispatcher or client delegates
to this entrypoint, nor process-wide security, cross-instance exclusivity,
crash durability, or arbitrary-Python bypass prevention. The next
integration investigation must identify the actual top-level dispatcher(s)
before making any global enforcement claim.

Before committing, validate the staged diff with `git diff --cached --check`
and confirm that only the three 24f files were staged.
