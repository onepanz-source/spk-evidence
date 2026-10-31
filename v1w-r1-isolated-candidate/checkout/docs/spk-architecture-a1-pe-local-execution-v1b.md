# SPK Architecture v1: A1b PE-Local Logical Execution

**Status: INTEGRATION PASS (2026-10-16, ideal logical PE domain).**

Baseline: A1a PE Fabric Placement, running on `spk-architecture-v1`.
Frozen reference tag: `spk-simulator-bounded-reference-v0`, commit
`a76ebaae49373a4c6b66f94465d78dbf1cf19f80`.

## Implementation

The A1b runtime **executes each neuron on its owning PE**, with independent
per-PE memory and event queue. A global logical arbiter chooses the earliest
`(timestamp, node_id)` from the heads of PE-local queues; each batch is
processed by the local PE interpreter, **not by the frozen Network**.

Emissions route to their declared PE target; every edge occurrence creates a
separate transport record and event delivery. Inter-PE transport is ideal:
`delivery_time = emission_time + declared_edge_delay`, with no additional
latency. No deduplication of parallel edges is allowed. The `single`, `split`
and `spread` placements are inherited unchanged from A1a.

## Independent semantic verification

- 216 pinned three-neuron corpus networks x 3 placements = 648 PE-local runs.
- Each local result is compared to an independently **compiled and executed**
  frozen Network through the 24t manifest host and to the 24n oracle, with
  canonical emissions, state, batches, routes, event counts and terminal outputs.
- Total source edge and dynamic route multiplicities are preserved.
- For this corpus the reference has exactly 768 remote route *occurrences*.
- Per-PE state custody and ownership, deterministic arbitration, invalid
  placement rejection and limit termination are independently tested.
- Cross-process canonical evidence replay and SHA-256 source pin required.

## Boundaries and non-claims

This is **PE-local execution** in an ideal single-process logical model, not
multiple parallel PE workers. The global logical arbiter is a deliberate
reference scaffold, not the future arbitration, mesh interconnect or service
clock. No independent physical clocks, PE capacity contention, backpressure,
service throughput bounds, persistent mailbox, ownership transfer, recovery,
learning or hardware behavior is claimed. A2/A3 will introduce the memory
and temporal service fabric; current `max_events` and `max_batches` are bounded
logical reference guards, not physical resource budgets.

The engine does not import Core, Compiler, Network, frozen host or independent
oracle. The **integration adapter** is permitted to call frozen Compiler/host
as the reference; it does not delegate PE-local execution to them.

## Gate

`bash search/spk_arch_a1b_final_gate_v1b.sh`

Six stages: pure 648-case differential; frozen Compiler/host integration;
canonical evidence replay across processes; A1a and cross-layer regressions;
whole-repository suite; architecture branch, immutable v0 tag and frozen
module preservation, whitespace and required-file hygiene.

No automatic commit or release tag is created.

## Roadmap

A1a establishes static mapping and PE admission; A1b establishes separate
PE-local state/queues with logical ideal transport. A1 remains open until
memory access, resource arbitration and PE-scale time are specified and tested.
A2 Memory Fabric and A3 Temporal Execution remain separate future stages.

## Certified A1b gate

- Independent PE-local tests: 11 PASS.
- Compiler/host integration tests: 7 PASS.
- Compiled host comparisons: 648.
- Cross-PE route occurrences: 768.
- Previous regressions: 30 PASS.
- Full repository regression: 3031 PASS.
- Independent-process replay: PASS.
- Frozen source preservation: PASS.

Evidence SHA256:
cecf79b4156cd863940e5bbf8b3b33f004ec27a01faf9dc019f16c75971b8128

Acceptance is limited to ideal logical PE execution.
No resource contention, physically timed transport,
backpressure or distributed clock is certified.
