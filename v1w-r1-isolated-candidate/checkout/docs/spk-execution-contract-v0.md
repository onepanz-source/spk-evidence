# SPK Execution Contract v0

Status: S1 ACCEPTED
Baseline: spk-core-network-v0
Branch: spk-simulator-compiler-v0

## 1. Scope

Define the boundary between SPK Compiler v0,
SPK Network v0 and SPK Simulator v0.

Frozen Core and Network semantics MUST NOT change.

## 2. Compilation

Input:
- Versioned declarative network description
- Node Core programs
- Node initial states
- Directed edges and delays

Output:
- Validated NetworkV0
- Canonical, versioned network representation

Requirements:
- Core programs must be runtime-normalized
- Core IR v0 is the authoritative node program encoding
- Invalid programs must be rejected
- No implicit creation of nodes or edges
- No semantic optimization in Compiler v0

## 3. Execution

The simulator delegates computation to run_network_v0.

Inputs:
- NetworkV0
- Tuple of NetworkEventV0
- max_batches
- max_events
- Optional observer

Outputs:
- emissions
- terminal_outputs
- states
- processed_batches
- processed_events

## 4. Temporal semantics

- Events are identified by timestamp, node and channel
- Batches group events by (timestamp, node_id)
- Channel multiplicity is preserved
- Channels are canonically sorted within a batch
- Node state persists across batches
- The Core guard is transient per batch
- Edge delay_ticks must be strictly positive
- Structural cycles are permitted
- Execution is subject to resource limits

Verified Core/Network temporal invariant:

- Every CoreEmit output has the batch timestamp.
- Therefore t_emit == t_batch.
- Every NetworkEdgeV0 has delay_ticks > 0.
- Therefore t_delivery > t_batch.
- SpikeTrain preserves timestamps and multiplicity.

These properties are supported by source inspection
and the execution-contract regression tests.

This does not constitute a formal proof of the
complete Core/Network semantics.

## 5. Routing

- An emission traverses every matching edge
- Parallel edges preserve multiplicity
- An emission without matching edges is terminal
- Routed events inherit the destination node/channel
- Routing delay is added to the emission timestamp

## 6. Observation

Available observation hooks:
- on_batch
- on_route

Observers must not intentionally modify execution.

Execution equivalence with and without an observer
must be established by differential tests.

Instruction-level tracing is outside v0.

## 7. Exclusions

- Learning algorithms
- Back-validation
- Plasticity
- New algebraic primitives
- Compiler optimization
- Physical hardware timing
- GUI
- Distributed execution

## 8. Acceptance criteria

S1:
- Interface contracts documented
- Temporal assumptions explicitly identified
- Baseline regression tests passing

S2:
- Versioned network source format
- Strict compiler validation
- Deterministic serialization
- Source-to-network reconstruction tests

S3:
- Compiler-to-runtime integration
- Reference network execution

S4:
- Non-interfering execution observations

S5:
- Differential and negative tests
- Reproducible execution artifacts

## 9. Compatibility rule

Any future extension must explicitly declare
whether it preserves the observable behavior
of SPK Core v0 and Network v0.
