# SPK Architecture A3a: Causal Inter-PE Transport v1a

**Status: INTEGRATION PASS (2026-10-16, bounded logical transport domain).**

## 1. Objective and ancestry

A1b establishes PE-owned neuron state and local input queues under an ideal
logical clock. A1c measures PE service on a separate service clock, and A2a-d
admit, authorize, serve and adjudicate aggregate logical P/S/E/O demands.
Neither service clock currently modifies the causal delivery of a spike.

A3a introduces explicit **causal in-flight custody** for remote spike occurrences,
without importing the frozen Core, Network, Compiler or the 24n oracle into its
new PE transport engine. It reuses A1b's admitted instruction fragment and
local `_compute_local`, rather than inventing a second neuron algebra.

## 2. Transport contract

`TransportPlanV1a(cross_pe_extra_ticks, max_inflight_occurrences)` has a
nonnegative integral per-remote-edge latency and a strictly positive finite
in-flight bound. For each emitted route occurrence:

- local recipient: delivery tick = emission tick + declared edge delay;
- remote recipient: delivery tick = emission tick + declared edge delay +
  `cross_pe_extra_ticks`;
- each parallel route yields a separate in-flight occurrence;
- inbound remote deliveries at timestamp T are installed into local PE queues
  **before** any ready batch at T is dequeued; batch multiplicity is retained;
- global chronological arbitration selects the minimum timestamp and node ID,
  and each neuron update uses its actual logical execution tick;
- the in-flight buffer must fully drain on successful closure; partial work
  before capacity overflow is not rolled back.

External inputs are preloaded at their declared ticks, and no external inputs
arrive asynchronously. Positive edge delays plus nonnegative additional remote
latency ensure event delivery does not travel backward in time.

When the extra latency is zero, the entire projected Network result must match
A1b and the independently compiled and executed frozen v0 reference on all
216 corpus cases × 3 PE placements. For positive latency, outcomes may differ:
state-decay operands and same-time input grouping can be affected. We do **not**
assert numerical equality to the zero-latency result.

## 3. Gate scope

- 216 source cases pinned to
  `cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`.
- 3 existing PE placements (`single`, `split`, `spread`).
- 3 extra remote latencies (0, 1 and 3 ticks): 1944 PE-local executions.
- 648 zero-latency comparisons with the frozen compiled/manifest/host reference.
- Isolated analytical chain witness at latency +2: C fires at t=3, 5 or 7
  for 1, 2 or 3 PEs.
- Remote-occurrence conservation, parallel edge multiplicity, same-tick
  coalescing, provenance and artifact replay.
- Fault injection: invalid transport plans and in-flight capacity overflow.

### 3.1 Failures

Transport admission errors and in-flight overflow are distinct. Capacity
exhaustion raises `TransportCapacityV1a` and yields **no complete result**.
No rollback, recovery, remote retry or at-least-once distributed delivery
mechanism is provided.

## 4. Explicit exclusions

This module models **only inter-PE logical transport latency**. It does not
couple A1c PE service wait, A2c memory service wait, or A2d post-execution
aggregate service adjudication into the neuron timeline. There is no link
bandwidth arbitration, congestion, active backpressure, persistent mailboxes,
distributed clock, failure recovery, hardware bus, or physical timing.

The finite DAG corpus cannot prove global deadlock freedom or equivalence on
arbitrary cyclic networks. An in-flight queue is not a durable network channel.

## 5. Acceptance

The authoritative gate runs all A3a tests against real frozen dependencies,
checks independently reproduced evidence, reruns prior A1b and A2d bounded
regressions and the full suite, then audits ancestry, immutable source domains
and file hygiene. No automatic commit or tag is created.

## Certified A3a gate

- Independent causal transport tests: 14 PASS.
- Frozen Compiler/host integration: 7 PASS.
- Temporal executions: 1944.
- Compiled reference comparisons: 648.
- Ideal cross-PE route occurrences: 768.
- Previous regressions: 24 PASS.
- Full repository regression: 3178 PASS.
- Cross-process canonical replay: PASS.
- Frozen-source and patch hygiene: PASS.

Evidence SHA256:
a8f94d1d729d0dfad728457e046fcac4d7110319ceea2156f0c224254b19f1f2

Acceptance covers causal logical inter-PE transport,
including zero-latency equivalence to frozen v0.

No causal PE/memory service contention, link bandwidth
arbitration, backpressure or recovery is certified.
