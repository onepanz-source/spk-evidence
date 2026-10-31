# SPK Architecture A3b: Causal PE Service Grants v1b

**Status: INTEGRATION PASS (2026-10-16, bounded global-arbiter domain).**

## 1. Objective and protected ancestry

A3a already makes inter-PE spike delivery causally dependent on declared edge
latency and extra remote transport latency. A1c measures finite PE batch
service on an **independent** service clock; A2c similarly arbitrates
**aggregated** logical P/S/E/O demands. Neither service tally can be added to
spike timestamps without a new temporal contract.

A3b establishes that contract for PE *batch service grants only*. It reuses
A1b's admitted local neuron instruction fragment (`_compute_local`), A1a's
ownership and A3a's remote route custody. Frozen Core, Network, Compiler,
Simulator, Architecture and oracle are neither imported nor modified by the
new runtime. A separate integration adapter uses the frozen compiled host only
as an external ideal-mode reference.

## 2. Causal clock and service policy

`CausalServicePlanV1b(pe_slots, fabric_slots_per_tick,
max_service_span_ticks)` declares positive integer service grants per PE and
per global arbitration tick, and a bounded causal service horizon.

1. External events enter their PE queue at the declared timestamp; in-flight
   remote deliveries due at T are installed **before** granting service at T.
2. Each group `(original_ready_timestamp, neuron_id)` retains all parallel
   events and its own identity, even if a delayed group is granted later.
3. At T an eligible PE group has `ready_timestamp <= T`. Among available PEs,
   the single global arbiter chooses the smallest
   `(ready_timestamp, neuron_id, PE id)`; it skips PEs whose grant quota is
   consumed. Both per-PE and shared grants are deducted for every batch.
4. The neuron executes at its **actual grant tick T**, and state
   `last_timestamp`, emissions and downstream delivery times use T. Hence
   wait can causally modify `SHIFT`/decay, grouping, and route ordering.
5. Every route occurrence retains its declared positive delay. Inter-PE
   occurrences add the explicit A3a remote transport latency, remain separate
   in-flight objects, and are delivered exactly once on successful closure.
6. Tick advancement jumps across empty gaps but never skips a pending ready
   group or an in-flight delivery. If the bounded service horizon expires,
   the execution raises `CausalServiceHorizonV1b` without a successful receipt.

**Clock semantics:** an A3b tick is a logical causal execution tick under a
single arbiter. It is not a wall clock or a model of genuinely concurrent
physical PEs. Delayed batches with *different* ready timestamps are not
retroactively combined just because they obtain service during the same tick.

## 3. Finite evidence domain

- Frozen source pin:
  `cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`.
- 216 finite three-neuron DAG cases, 3 PE placements.
- Two transport extra latencies: 0 and 2 ticks.
- Four service regimes:
  - ideal: 128 PE / 128 fabric grants per tick;
  - PE-limited: 1 PE / 128 fabric grants per tick;
  - fabric-limited: 128 PE / 1 fabric grant per tick;
  - jointly limited: 1 PE / 1 fabric grant per tick.
- 5,184 causal PE service executions; 1,296 exact A3a ideal-profile
  comparisons; 648 zero-latency independent Compiler/host comparisons.
- Invariants: event-occurrence conservation, remote-delivery conservation,
  nonnegative grant wait, quota conformance, canonical per-grant and per-route
  ledger hashes, service-horizon failure and remote in-flight overflow.

No equality between finite-capacity and ideal results is asserted. A changed
result is **expected** if service contention delays a relevant neuron; this
is an actual causal change rather than A1c's separate accounting statistic.

## 4. Deliberate limitations

A3b does not couple A2a–d *memory* transactions or A2c bandwidth limits into
its causal pipeline. It implements no link bandwidth arbitration,
credit-based backpressure, bounded local event queue, distributed scheduling,
asynchronous PE failure, recovery, rollback, delivery retry, or hardware
throughput. Its global deterministic grants are a bounded reference policy,
not proof of optimal fairness on arbitrary networks. Its verified corpus is
finite, acyclic and three-node, not general cyclic network correctness.

## 5. Acceptance and gate

The authoritative six-block `fwork` gate runs independent A3b runtime tests,
real frozen Compiler/host comparisons, process-independent sealed evidence
replay, A3a/A1c regression, the complete repository suite and frozen-source
hygiene. No automatic commit or tag is created.

## Certified A3b gate

- Independent causal PE tests: 20 PASS.
- Frozen Compiler/host integration: 7 PASS.
- Causal service executions: 5184.
- Frozen compiled host comparisons: 648.
- Ideal A3a comparisons: 1296.
- Previous regressions: 39 PASS.
- Complete repository regression: 3205 PASS.
- Independent-process evidence replay: PASS.
- Frozen-source and patch hygiene: PASS.

Evidence SHA256:
b3fec71b9e54b7adff4cbe2b89f28fff774c62aba56d5bceade3ecc48f6b0891

Changed temporal executions per 1296-run regime:
- Ideal: 0
- PE limited: 162
- Fabric limited: 354
- Joint limited: 354

Acceptance covers causal finite PE service grants,
including their influence on neuronal execution
and inter-PE spike delivery.

No causal memory transaction service, link bandwidth
congestion, backpressure or physical timing is certified.
