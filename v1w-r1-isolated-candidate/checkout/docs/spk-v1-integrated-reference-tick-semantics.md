# SPK V5 T8STU/VWX/YZA: integrated reference v1 ticks (research)

Status: additive research code. **NOT native SPK Back Validation, NOT native
SPK Memory Contract v0 admission, NOT native SPK learning.**

## Contract boundary

The original `spk_architecture_v1/pe_execution_v1b.py` kernel function
`_compute_local` remains byte-identical and executes C, B and A. The original
BV-v0e scheduler remains byte-identical, called **after** a completed episode
only as a read-only parity oracle. A new `TickEngine` is the owner of the V1
reference event queue and P reference state, and it alone authorizes reference
P writes. The original frozen scheduler does not inherit these capabilities.

### T8STU: one event per tick

At tick 10 C emits (11/12), at tick 11 B relays (13/14), at tick 12 A
computes via frozen PE semantics and emits verdict (21/22) + terminal (7).
The new scheduler places an independently queued semantic A→B message at tick
13, then B→C at tick 14. These are **new v1 reference semantic events**, not
native v0e BV packets. All five events have explicit receipts and durable
transactional queue state in SQLite. The current v1 reference supports only
one active three-node episode, an idealized clock and no PE contention.

### T8VWX: P commit within receiving tick

On the `SEM_B_C` event, the C-owned P reference authority checks the decision,
policy version, event lineage, typed A verdict, update budget, deadline and
replay uniqueness. An accepted *negative* verdict may issue a reference P grant
and update the context policy in one SQLite transaction. The future C PE event
reads the updated reference P. The authority runs inside the new research
scheduler's event loop. There are no native SPK Memory Contract grants.

The queue persists between tick steps. Crash/reopen after A evaluation and
before B relay completes feedback precisely once. Receipt by tick 18 allows
P adaptation; tick 19 onward preserves the verdict but denies the P grant.
The whole process remains host-controlled; WAL FULL does not attest the host.

### T8YZA: independent oracle, controls, restrictions

For a source projection, run **the actual frozen BV-v0e scheduler** on the same
C choice and A goal *after* each research episode has settled. Check A PE
verdict, structural A→B→C deliveries, and the exact SHA-256 sequence archived
by the prior T8JKL/MNO/PQR report. The oracle cannot send inputs back to the
new scheduler. In local environments with missing original admission modules,
this full SHA parity step is not considered passed, even if PE behavioral tests
pass with admission stubs.

Source-pinned positive control: 88/96 successes and eight V1 reference tick P
commits, versus 48/96 and zero commits in the fixed baseline. Lost C→B
forward route: zero A verdict and zero grants. The host can change the
synthetic A goal with an identical C choice, changing the verdict and grant;
there is no authentic physical observation and no independent native trust.

## Nonpromotion criteria

- `native_BV_semantic_deliveries = 0`
- `native_SPK_P_grants = 0`
- `native_SPK_P_writes = 0`
- `native_learning = false`
- `promotion_allowed = false`

For future actual adoption, a separate versioned integration with the
Architecture Memory Contract, real scheduler admission and a justified trust
boundary is required. Frozen BV-v0e and PE v1b remain unchanged.
