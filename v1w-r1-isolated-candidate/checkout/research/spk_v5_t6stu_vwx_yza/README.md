# SPK V5 T6STU + T6VWX + T6YZA: experimental owned-C persistent state

This is **one cumulative additive research milestone** with one reproducible gate.
Only `research/spk_v5_t6stu_vwx_yza/` and the new `search/` launcher are added.
No frozen SPK Core, Network, Compiler, Architecture, PE, memory contract, or
Back Validation scheduler source is changed.

- **T6STU: C-owned P-state adapter.** An explicit C/PE-ID/memory-domain
  scope, SQLite WAL (`synchronous=FULL`), transactionally versioned policy
  entries, issue/vote/settle/close events, two-receiver quorum and bounded
  update budget. Every C action and return uses the unchanged frozen PE
  `_compute_local` through the previous research path.
- **T6VWX: deterministic parity and recovery.** Eight inherited 96-case
  experiments versus T6JKL/MNO/PQR, both uninterrupted and with reconnect
  after every four-decision batch; ten jitter seeds with reopens, exact trace,
  output and transcript parity. No promotion of model-only effect.
- **T6YZA: adversarial state/custody.** Reopen after one pending vote,
  commit-once and at-most-once detection, version mismatch rejection, rollback,
  process restart with another interpreter, materialized-state and ledger
  corruption detection, plus the **mandatory host impersonation** that still
  succeeds in producing a complete forged pair of votes.

The state owner is C **within this experiment**, not the actual frozen SPK P
memory allocator, not a hardware-isolated PE and not the native BV scheduler.
A privileged host may rewrite the entire SQLite DB and reconstruct a coherent
ledger, impersonate A/D, or author arbitrary target goals. Ledger SHA-256 means
internal integrity checking, not authentication. There are no independent
sensor observations, no native BV credit, and no native learning.

## Running

From `~/workspace/spk-backvalidation-v0` (after extracting):

```bash
bash search/spk_v5_t6stu_vwx_yza_cumulative_gate.sh \
  ~/workspace/spk-evidence/spk-v5-t6stu-vwx-yza-cumulative.json
```

The gate fails closed if its report already exists, if any ancestor manifest,
12-source pin or frozen PE/BV hash drifts, or if the previous T6 report cannot
be reproduced byte-exact. A clean local source package that lacks the full
frozen 12-source checkout can run the **27 new unit tests**, but not the strict
full gate. On `fwork`, use the full gate.
