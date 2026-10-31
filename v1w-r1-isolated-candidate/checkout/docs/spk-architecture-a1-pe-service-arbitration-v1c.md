# SPK Architecture v1: A1c Finite PE Service Arbitration

**Status: INTEGRATION PASS (2026-10-16, separate service-clock domain).**

Frozen reference: `spk-simulator-bounded-reference-v0` at
`a76ebaae49373a4c6b66f94465d78dbf1cf19f80`.

Upstream A1a: static PE placement and Compiler resource admission.
Upstream A1b: real PE-local state, event queues, and independent Core-fragment
computation with ideal transport.

## New contract

A1c introduces a **finite, deterministic, rate-limited service plane** that
executes each logical batch on its owning PE. The event clock and service clock
are explicitly different:

- The logical arbiter always selects the smallest `(timestamp, node_id)` from
  the heads of the independently owned PE queues, exactly as in A1b.
- A selected batch requires **one global fabric grant** and **one local PE
  grant** at the chosen *service tick*. Each grant consumes one configurable
  positive capacity slot. The virtual service clock is monotonic and never
  earlier than the logical event timestamp.
- If either capacity is exhausted, the service tick advances deterministically
  until both grants are available. The service ledger accounts for the delay,
  and records the node owner, logical timestamp and grant time.
- **Logical spike time is not shifted by service waits.** Every edge still
  delivers at `emission_timestamp + edge.delay_ticks`, with occurrence
  multiplicity intact. This choice isolates capacity accounting and does
  **not** claim physical-time causality or queue backpressure.
- Per-PE event queue occupancy has an independently configurable hard cap.
  Exceeding it raises `PEQueueOverflowV1c`; no partial result is published.
  There is no transaction rollback or recovery protocol.
- Core execution uses `_compute_local` from the separately developed A1b
  interpreter. Neither the A1c engine nor A1b imports or executes the frozen
  Network, Compiler, host or differential oracle. Integration adapters may
  use those components to verify A1c externally.

The service ledger is a *resource witness*, **not an architecture timing
prediction**: in a physically timed architecture delayed PE service might
shift spike release or cause buffers to saturate. That causal coupling, and
any active backpressure, belong to A2/A3, not A1c.

## Conformance domain

Pinned 24o corpus: 216 three-neuron DAGs, SHA-256
`cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`.

Three admitted placements: `single`, `split`, `spread`. Four service regimes:

1. Shared fabric and per-PE grant limits: 1 slot/tick each.
2. PE-only limit: 1 local slot/tick, generous fabric capacity.
3. Fabric-only limit: 1 shared slot/tick, generous local capacity.
4. Unconstrained reference: generous fabric and local capacity.

For each of **648 independently compiled placement references**, the new
engine executes **four** service regimes, giving **2,592 PE-service runs**.
All must match A1b and the independently compiled frozen v0 host exactly for
logical emissions, terminal outputs, state, event/batch counts, and routes.
The four ledgers must obey configured slot caps independently. At least one
finite regime must exhibit PE contention and one must exhibit fabric contention.
The unconstrained regime must have zero service wait and zero stalls.

Additional negative tests reject invalid service plans, wrong owner/custody,
initial and routed queue overflows, premature event/batch limits, and forged
canonical evidence even after hash recomputation.

## Explicit non-claims

- No parallel workers, physical processor cycles or independent PE clocks.
- No service-time feedback into spike arrival timestamps.
- No active backpressure, retry, admission fairness or deadlock recovery.
- No bounded durable mailbox, no checkpoint/rollback and no persistent owner.
- No Memory Fabric P/S/E/O arbitration (A2) or Network-on-Chip timing (A3).
- No universal invariance outside the 216-case finite source domain.

## Gate

`bash search/spk_arch_a1c_final_gate_v1c.sh`

Six stages: pure resource service and overflow; real frozen Compiler/host
comparisons; two independent process artifacts and replay; A1a/A1b
regressions; complete repository suite; frozen-reference and hygiene checks.
Gate does not create commits or tags.

## Roadmap

A1a and A1b provide PE ownership and PE-local logical computation. A1c tests
finite service capacity with observational scheduling, so A1 remains open.
A2 will define explicit P/S/E/O memory resource allocation and contention;
A3 will define causally timed spike transfer and backpressure policies.

## Certified A1c gate

- Independent service tests: 12 PASS.
- Compiler/host integration tests: 8 PASS.
- Compiled reference comparisons: 648.
- PE-service executions: 2592.
- Prior A1a/A1b regressions: 48 PASS.
- Full repository regression: 3051 PASS.
- Independent-process evidence replay: PASS.
- Frozen-source and patch hygiene: PASS.

Evidence SHA256:
9e35bef1a9c7f8b4db89831fdeeb79098f3072618d791cdb02b809eae23a7082

Regime totals:
- PE + shared limited: PE stalls 398, fabric stalls 642, wait 789.
- PE limited: PE stalls 267, fabric stalls 0, wait 316.
- Shared limited: PE stalls 0, fabric stalls 642, wait 789.
- Unconstrained: zero stalls and zero service wait.

The service clock does not alter logical spike timestamps.
No causal backpressure or physical execution timing is claimed.
