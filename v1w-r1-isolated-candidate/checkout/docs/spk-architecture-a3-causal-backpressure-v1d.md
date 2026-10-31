# SPK Architecture A3d: Causal Link Backpressure v1d

**Status: INTEGRATION PASS (2026-10-16, bounded sender-FIFO logical link domain).**

## Contract and continuity

A3d is a separate experimental engine built on A3c's conservative causal
memory-permit execution, A3b's finite PE grants and A3a's logical transport.
It leaves all frozen v0 modules and all earlier A1/A2/A3 sources untouched.
It executes the same three-neuron, bounded DAG corpus. The arbiter remains a
single deterministic logical authority, **not** a distributed NoC or clock.

The controller specifies positive **per-directed-PE-link** grants per tick,
**global link fabric** grants per tick, a bounded **sender outbox** for each PE,
and a positive **service horizon**. The A3a in-flight occurrence capacity
remains active. These capacities are logically distinct:

1. A remote occurrence is created by an actual neuron emission and stored in
   the source PE's FIFO outbox; its target edge multiplicity is never collapsed.
2. Link injection consumes one directed-link and one shared-fabric credit.
   Only an injected occurrence occupies an in-flight slot; both quotas and
   in-flight space must be available at the injection tick.
3. Injection at tick `g` creates a delivery at
   `g + declared_edge_delay + cross_pe_extra_ticks`, rather than delaying an
   already computed receiver output after the fact.
4. The receiver enqueues each occurrence individually at that tick, before PE
   batches at the same tick. A sender **cannot execute its next batch while its
   outbox is nonempty**. Backpressure therefore changes PE-grant timestamps.
5. Local routes bypass remote link credits and keep their declared delay.
6. Sender FIFO is preserved. Across source PEs the global arbiter uses fabric
   PE order. Link credits reset per logical tick; no event is silently lost.

An entire batch's remote fanout must fit into an empty bounded sender outbox,
otherwise `CausalOutboxCapacityV1d` is raised *before neuron state mutation*.
Service horizon exhaustion raises `CausalLinkHorizonV1d`; neither error claims
`CLOSED`, rollback or durable recovery. Memory envelopes granted before
computation cover possible `ROUTE_ENQUEUE` intents, while transport injection
and delivery have separate timestamps and custody. A2/A3 memory intent counts
remain abstract logical accesses, **not physical RAM transactions**.

## Invariants / certification intent

- Unlimited directed links, fabric grants and in-flight capacity reproduce
  **A3c result and route transcript exactly**, for both tested latencies.
- `processed_events = external_input_occurrences + routed_occurrences` at
  completion; each injected remote occurrence is eventually delivered once.
- Every remote link grant has an identified sender, target, source/target
  channels, emission tick and actual delivery tick. Congestion waiting time is
  `link_grant_tick - source_emission_tick`, and must be nonnegative.
- Finite in-flight occupancy never exceeds its configured maximum; source
  backpressure occurs instead of silent transport loss.
- No false `CLOSED` output after invalid quotas, insufficient outbox capacity,
  or exhausted logical service horizon.
- Frozen Compiler and host witness *ideal latency-zero* runs. A3c witnesses
  uncongested latency-zero and latency-two runs. Congested results are
  independently recomputed, **not** required to match the ideal reference.
- Source-pinned evidence must be reproducible across independent processes;
  canonical, checksum and full semantic replay are all required.

## Deliberate limitations

- No receiver-side ingress-queue quota and no credit-return protocol.
- No true concurrent execution, physical bandwidth/energy, cache/bank
  contention, or distributed synchronization.
- The source outbox can hold a complete burst, but capacity insufficient for
  a single burst fails explicitly; it does not stall inside an instruction.
- Event occurrence conservation does **not** mean equal outputs across
  different timing regimes: time-sensitive programs can emit differently.
- No recovery, dynamic PE reassignment, cancellation or rollback.
- Limited deterministic 216-case corpus, not a proof for arbitrary topologies.

## Acceptance

The bundled gate covers pure engine behavior, real frozen Compiler/host
comparison, independent-process canonical replay, earlier causal regressions,
full repository regression and frozen-source/staging hygiene. Run it on the
`spk-architecture-v1` worktree after committing the certified A3c files.

## Certified A3d gate

- Independent causal link tests: 20 PASS.
- Frozen Compiler/host integration: 7 PASS.
- Causal link executions: 3888.
- Ideal A3c comparisons: 1296.
- Compiled host comparisons: 648.
- Previous A3 regressions: 53 PASS.
- Full repository regression: 3259 PASS.
- Independent-process canonical replay: PASS.
- Frozen source and patch hygiene: PASS.

Evidence SHA256:
38ad466b0eea78f83118498519069452cad934e5c0fa695128bf83e15372bdac

Limited regime observations:
- Link-limited: 371 changed runs, 628 link wait ticks,
  624 source blocked ticks.
- In-flight limited: 371 changed runs, 3263 link wait ticks,
  2735 source blocked ticks.

Acceptance covers sender-owned FIFO outboxes, finite
logical link credits, causal backpressure and event
occurrence conservation.

No receiver ingress quotas, physical NoC, distributed
clock, asynchronous recovery or rollback is certified.
