# SPK BV v4an–v4ap — Bounded research closure and evidence handoff

**Scope is CLOSED as a reproducible research protocol, NOT as a validated,
deployable, self-learning neuromorphic system.** This distinction is the
central result of the milestone. There is no promotion of frozen Core,
Network, Compiler or Architecture v1 contracts, no mutation of native v0e,
no source-identity weights and no adoption of modified neuron programs.

## What the evidence establishes

- Frozen native forward and BV computations, native causal replay and the
  separate actor/ACK transport have reproducible, previously signed witnesses.
- Bounded PE/link admission, credit custody, priority contention, fairness,
  finite-horizon tails and replay exclusion were tested without conflating
  synthetic acknowledgments with native decisions.
- The task objective is expressly **synthetic**. Two observational views
  derive from the same native evidence, so agreement does not provide
  independent real-world correctness. Controlled reversal of synthetic labels
  can reverse qualitative rankings.
- Typed reviews and SQLite escrow were exercised across 198 attempts and 72
  committed journal entries (144 distinct replay nonces); concurrent duplicate
  attempts, crash, restart, replay and tampering were rejected.
- Two separately valid SQLite forks can disagree while each passes local
  integrity checks. An independently *retained digest in the test* detects a
  divergent valid fork and rollback. The public fixture HMAC key, same-host
  capsule and report are **not** independently held trust credentials.
- No neuron has adopted an algorithm change: `program_adoptions=0`.

## Closure test

The closure gate re-executes 19 new release boundary/adversarial tests and all
199 inherited v4m–v4am tests (218 unit tests), plus a frozen-native v0e smoke.
It validates byte-exact signed predecessors, all 15 source/fixture file hashes
in the v4akam release manifest, the local SQLite state against the held
capsule digest, the valid-fork/rollback counterexample and a byte-identical
reference closure observation. Source/report changes or unsafe/symlinked
inputs must fail closed. The resulting JSON is exclusively created outside
the repository and does not grant any runtime permissions.

The 199 inherited count refers to the nine explicitly enumerated cumulative
test suites, **not** to every test in the entire repository. Individual gate
success on fwork is required before the milestone is accepted there.

### Evidence-level acceptance criteria (all eight required)

1. Frozen native and previous release source/fixture pins match.
2. Prior native forward and feedback reexecution is traceable.
3. Prior bounded actor/ACK, credit, priority and fairness work is traceable.
4. Reopened escrow matches 72 records and 144 unique nonces.
5. Retained digest rejects another locally valid SQLite branch.
6. Retained digest rejects rollback to a valid earlier branch.
7. Canonical closure observation is reproducible from signed input bytes.
8. No native program adoption is introduced.

## What remains unproven (external validation phase)

| Requirement | Result | Needed independently of this repository |
| --- | --- | --- |
| External anchor | NOT PRESENT | A different owner with protected signing keys, an authenticated monotonic head, independent publication and recovery rules |
| Issuer identities | NOT PRESENT | Provisioned verifiable identities, revocation and key rotation |
| Task correctness | NOT PRESENT | Pre-registered independent real task holdout, defensible outcome labels and noncorrelated evidence |
| Learning effectiveness | NOT ESTABLISHED | Prospective task results and matched controls; error bars, negative cases, generalization/overfit monitoring |
| Native learning authority | NOT IMPLEMENTED | Separately reviewed change policy, safe adoption/rollback/rollback tests, operational vetoes |
| Hardware/mesh claims | NOT EVALUATED | Hardware profiling, memory/energy/latency and loss/jitter experiments after architecture decisions |

Do **not** replace absent evidence with another synthetic reviewer, key, oracle
or same-host database: that would add mechanisms but would not answer the
missing scientific questions. A future, separately authorized external
validation phase may import the frozen evidence bundle as a baseline; it must
not reinterpret this closure as a production safety or generalization claim.

## Freeze boundary

- **Frozen:** current bounded BV research protocol, source-pinned observations,
  terminal causal/native replay, actor transport/custody and synthetic task
  observational scaffolding.
- **Excluded:** real autonomous algorithm/policy adoption, physical trust
  custody, real learning metrics, Σ/σ separation, source-dependent semantic
  weights, distributed mesh timing/noise/loss and hardware choice.
- **Handoff:** `NEW_VALIDATION_PHASE_REQUIRES_EXTERNAL_OWNER_AND_TASK_TRUTH`.

The remaining work is no longer “one more synthetic BV protocol improvement.”
It is *independent evidence*. The research-only chapter can end at this
boundary without prematurely declaring the architectural learning problem
solved.
