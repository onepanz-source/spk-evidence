# SPK v1 research: bounded concurrent-epoch admission & versioned P

Status: **research reference ONLY**. No mutation or promotion of frozen Core,
Network, Architecture v1, PE, Memory Contract, BV-v0e or original source pins.

## T9ABC: concurrent epochs under finite reference admission

- `MultiTickEngine` allows at most `max_inflight` unsettled episodes (1..8).
- All admission and state changes use SQLite `BEGIN IMMEDIATE` transactions.
- Pending event ordering is FIFO by immutable event ID. This prevents newer
  early local ticks from overtaking older delayed local feedback indefinitely.
- Each processed event obtains a unique durable `DISPATCH_SLOT` ledger entry.
- **Tick 10/11/12/13/14 and feedback delays are local to an episode**. Different
  episodes using tick 10 are not simulated as simultaneous physical PE cycles.
- A dispatch slot is a research serialization unit, not device latency, PE
  throughput, hardware admission or native SPK authority.

## T9DEF: version-bound feedback under competition

- C snapshots its context policy choice and version when it issues a decision.
- A generates a semantic verdict through the frozen PE primitive, then A→B→C.
- On B→C, an atomic version/choice comparison is made against current C P.
- The first matching negative verdict may receive a **reference-v1 P grant**
  and update P atomically; later verdicts against old versions still settle
  as evidence but receive `VETO_STALE_POLICY` and **zero additional credit**.
- Context 0 and context 1 are versioned independently.
- A crash between steps does not bypass the replay/one-commit rule.

## T9GHI: evidence and counterexamples

- 96 episodes in four synthetic regimes. Serial and paired tests give 88/96,
  while triple admission gives 84/96 and four stale verdict vetoes. This loss
  is a genuine concurrency cost within the model, not a test failure.
- Control policy 48/96; complete feedback removal 48/96.
- Admission exhaustion is fail-closed; a delayed feedback after local tick 18
  can be observed but cannot authorize P.
- Source provenance is bound to the preceding T8 report SHA and exact frozen
  PE/BV file hashes; 12 original source pins are checked on fwork.
- Every end-to-end report has `native_SPK_P_grants=0`,
  `native_BV_semantic_deliveries=0`, `native_learning=false`.
- The privileged host still controls synthetic goals and the SQLite database;
  resealing host-controlled state is not cryptographic attestation.

## Not established

No hardware PE contention or global time model; no native SPK Memory Contract
admission; no general multi-neuron topology; no 4-node BV-v0e support; no
independent A sensor authority; no general learning theorem. New native versioned
scheduler work still requires a separately approved SPK contract/release gate.
