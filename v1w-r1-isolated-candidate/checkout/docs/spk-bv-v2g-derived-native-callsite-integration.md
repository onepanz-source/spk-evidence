# SPK/* BV v2g: Derived Native Callsite Integration and Differential Gate

## Scope

This is a substantive **native-derived execution** experiment, not a new
independently modeled `relay/pair/block` micro-scheduler. A read-only parser
loads the already pinned `live_dual_scheduler_v0e.py`, selects only
`execute_live_v0e` with its seven frozen positional parameters and validates
four previously audited call sites by **name and line** (`_admit`:49,
`_admit_plan`:50, `offer_feedback`:150 and 206). An AST transformer wraps the
callee *expression* at these four sites, without replacing arguments, returns,
operation operands or control configuration. The transformed function is
compiled **in memory** under a new research name using an isolated globals
map, keeping original imported classes, plans and functions. Neither frozen
source nor its runtime module globals are modified.

The metadata callback records only which *derived scheduler callsite* returned,
its source line and a bounded ordinal. The feedback call-site `offer_feedback`
is **not** a certificate that neuron B issued a local value judgment or that a
sender received information. The listener does not see authenticated spikes,
operator identities, source events, semantic delivery, reliable absences, or
cryptographic trust.

## Full gate (on fwork)

The native CLI requires the canonical v2e and v2f signed-off reports exactly as
uploaded (SHA-256 pinned), plus four source hashes and the source hashes of
the two new v2g research modules. It conducts 15 historical workloads × 3
control policies:

- **45 unmodified native executions** with complete byte-independent result
  summaries equal to the v2e attestation;
- **45 in-memory derived native executions** with call-site metadata enabled
  and **complete result summaries** equal to the same native executions;
- **45 derived runs with a raising observer sink**, verifying output parity and
  explicit observer-fault status;
- **45 derived runs with a capacity-one observer**, verifying output parity,
  overflow and incomplete evidence.

Total: **180 runtime executions**, 135 running the derived function. All
frozen input/fixture/source hashes are checked for drift. The four call sites
must be uniquely auditable, otherwise the gate rejects without a positive
attestation. The produced JSON distinguishes interpreter instrumentation,
which is experimental, from native recipient messages, which remain zero.

## Failure/authority rules

- Unknown source SHA, AST signature, duplicated site, lost mandatory site,
  unexpected new call, missing report, corrupted predecessor, existing output,
  mutated fixture, mismatched native digest/metrics: **REJECT**.
- Observer sink exception or collector overflow: forward/BV may continue but
  observation is explicitly marked **incomplete**. No absence verdict.
- No hooks are connected to the frozen scheduler and no frozen contracts
  are promoted. A full parity PASS is restricted to the 15×3 finite matrix.
- `offer_feedback` is a scheduler callsite name, not a producer-owned
  semantic feedback event. The stored metadata is a research observation;
  the ten native BV proof obligations do not become automatically satisfied.

## Acceptance decision

The release advances our **validation tooling** to a runnable native-derived
comparison. It does **not** itself close native receiver delivery, endogenous
judgment, causal credit, operator commit/rollback or native learning.

The next functional checkpoint must be a *separately versioned native fork with
explicit semantic event and receiver mailboxes*, using this parity evidence as
its forward/scheduling gate. Integrating into the frozen executor remains
forbidden without a separate review and freeze change process.
