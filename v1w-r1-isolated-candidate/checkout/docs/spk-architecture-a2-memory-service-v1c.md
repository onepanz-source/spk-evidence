# SPK Architecture v1: A2c Finite Memory Service Arbitration

**Status: INTEGRATION PASS (2026-10-16, bounded aggregate-demand domain).**

Baseline: frozen `spk-simulator-bounded-reference-v0` at
`a76ebaae49373a4c6b66f94465d78dbf1cf19f80`.

## 1. Scope and architecture boundary

A2a reserves abstract memory capacities for P (program), S (state), E
(events) and O (observations). A2b derives activity-bound, epoch-scoped
logical access demands from independently checked A1d/A2a committed traces.
A2c **never bypasses A2b**: it checks the identical admission, authority,
and authorized request sequence, then produces a deterministic *accounting
service ledger* under finite memory service quotas.

A2c is neither an enforcement layer intercepting live memory accesses nor
an implementation of actual RAM banks, caches or memory controllers. A2b
holds only *aggregated* counts, not ordered transaction timestamps. Thus
all A2c demands are notionally ready at service tick 0. These service ticks
are distinct from both SPK logical spike timestamps and A1c PE-service ticks.
They never delay spikes or alter neuron states in this contract.

## 2. Explicitly distinct policy dimensions

- **Admission and ownership**: A2a gives each PE P/S/E/O reservations.
- **Authorization**: A2b checks activity, epoch, PE, domain and intent.
- **Priority**: A2c uses a trusted controller's ordered permutation of
  P/S/E/O. The default *experimental A2c* order is E, S, P, O, not an
  algebraic SPK rule and not a training/verify/remodel policy.
- **Service**: per-PE, per-domain and fabric-wide positive integer quotas
  bound grants per service tick. Within a domain PE order rotates each tick;
  within a PE, original A2b request order is deterministic.

The priority is supplied only in the trusted service plan. Caller requests
cannot self-assign priority or obtain access through the scheduler.

## 3. Quantities and conservation

For every positive A2b logical intent quantity A2c issues exactly that many
service units. Zero-quantity `EMISSION_RECORD` occurrences remain zero
accounting rather than generating grants. Parallel route occurrences retain
their multiplicity. The ledger records (tick, PE, domain, request, quantity),
per-PE and per-domain totals and unit-weighted wait ticks. *Wait* measures
only this aggregate-demand experiment, not physical latency.

If `max_service_ticks` is insufficient, A2c raises
`MemoryServiceExhaustedV1c` without a completed service receipt. When a
prefix has `execution_status=PE_FAULT`, completed memory-service accounting
does not transform the neuron computation into `CLOSED`.

## 4. Verification corpus

Source corpus SHA256:
`cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`.

- 216 canonical compiled networks at three PE placements: 648 reference
  Compiler/host comparisons and authorized nominal memory demand ledgers.
- Two service regimes for each nominal result: 1,296 nominal memory-service
  projections (finite and abundant budgets).
- 504 reachable pre-grant PE fail-stop prefixes also served as *prefix
  accounting* rather than successful neural execution.
- Negative checks cover rejected grants, forged quantities/priorities,
  epoch and PE ownership mismatches, invalid capacities and service budget
  exhaustion, plus replay and digest recomputation forgery.
- Canonical, source-pinned evidence regenerated in independent processes.

## 5. Explicit non-claims and next contract

A2c does **not** demonstrate physical bandwidth, cache locality, memory
consistency, transaction atomicity, starvation freedom, causal stall/backpressure,
mode-dependent priorities, concurrent host-thread safety, permission checks
at every real memory read/write, or persistent replay. A2d must address
memory exhaustion and safe failure under a versioned resource policy;
A3 must later define actual causal timing semantics. P/S/E/O abstract
resource units are not bytes.

## 6. Gate

`bash search/spk_arch_a2c_final_gate_v1c.sh`

Six stages: independent memory service tests; frozen Compiler/host
integration; independent-process evidence equality and replay; previous A2b,
A2a and A1c regressions; complete suite; frozen boundary/patch hygiene.
No commit or tag is created.

## Certified A2c gate

- Independent memory service tests: 18 PASS.
- Frozen Compiler/host integration: 7 PASS.
- Compiled reference comparisons: 648.
- Nominal service executions: 1296.
- Fault-prefix service executions: 504.
- Previous A2/A1 regressions: 39 PASS.
- Full repository regression: 3137 PASS.
- Cross-process evidence replay: PASS.
- Frozen-source and patch hygiene: PASS.

Evidence SHA256:
2edce982d5a543d4a2342356fd6649ae4fcc549326b13ee28520b8f98d777140

Limited weighted service wait: 118948 ticks.

Acceptance covers deterministic finite service of
A2b-authorized aggregate logical memory demands.

No live transaction enforcement, causal memory stalls,
physical RAM timing or backpressure is certified.
