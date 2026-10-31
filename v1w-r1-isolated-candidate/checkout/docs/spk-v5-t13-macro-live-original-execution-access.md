# SPK V5 T13 Macro · Original execution access inside reference C ticks

## Scope and non-promotion
T12 v1d demonstrated 4 original chains of A1d execution, memory admission,
projection, access authorization, and memory service. Those chains were
separate from the reference P scheduler. This macro changes the *new research*
version only: the C `SEM_B_C` update calls the actual original T12 chain for
the same `(choice, goal)` **inside its SQL admission callback**, before a
reference-owned P commit. The callback must return an original-access witness
and never a frozen SPK P-learning grant. Failure aborts all event/grant/P
mutations atomically.

The SQLite `AFTER INSERT` trigger records the witness in the same transaction,
keyed by grant ID, exact policy version, semantic C event, episode, choice,
and goal. Reopen/audit rejects broken scope, missing witnesses, tampered SQL,
and test-mode/production-mode mixing. The original source SHA and original
A1d producer SHA are pinned, and real original A1d output is required.

## Deliberate tradeoffs
The existing T12 proof routine processes **four original choice/goal cases**
per candidate P commit, and selects the exact matching row. This costs 32
original A1d executions for 8 original access witnesses, but avoids redesign
of the pinned T12 bridge during this macro. The gate repeats the deterministic
report and counts only the **eight matching** authorized receipt witnesses.

Original A1d events are invoked on a newly constructed matching three-neuron
case, **not** on the already-running host-generated C epoch. This is an
execution-memory prerequisite, not evidence that the original scheduler
itself issued, received, authenticated or learned from BV feedback.

The original frozen Memory Contract does not grant a learning P update.
All eight modified P policies remain controlled by the new reference V1.
The host may rewrite SQLite or the synthetic A goal. There is no independent
signal authentication, global clock, physical PE timing or generalization.

## Release gate
- Parent T12 fwork report SHA-256 and 24 cumulative source manifests verified.
- Original PE, BV, A1d and 5 Memory API source SHA pins preserved.
- 35 new negative/integration tests and inherited 23 cumulative suites.
- Two strict runs with original APIs, byte-for-byte parity and 8 matching
  original access witnesses in reference C tick transactions.
- No `--local-test-only` in release; test-generated witnesses are always
  counted separately and cannot promote original access or learning.

## Explicit next architectural target
A future SPK-owned runtime scheduler must issue authenticated BV semantic
observations to an independently anchored recipient and an *actual P learning*
authority. Execution-memory access can serve as a prerequisite, but cannot
itself authorize that learning transition.
