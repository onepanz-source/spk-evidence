# SPK Simulated Neuromorphic Architecture v1: A1a PE Placement Conformance

Status: INTEGRATION PASS (2026-10-16, static mapping domain).
Branch: `spk-architecture-v1`, separate worktree.
Frozen baseline: annotated tag `spk-simulator-bounded-reference-v0`
(`a76ebaae49373a4c6b66f94465d78dbf1cf19f80`).

## Scope

This is **A1a (static PE fabric placement)**, not the complete A1 execution
fabric. Frozen `spk_architecture.profile_v0`, `spk_compiler.pe_admission_v0`
and compilation manifests remain the source of truth for capacity admission.
No second PE admission contract is introduced.

Each of 216 source cases in the pinned 24o corpus is compiled under exactly
three homogeneous overprovisioned architecture profiles:

- `single`: A, B, C placed on PE0;
- `split`: A on PE0, B and C on PE1;
- `spread`: A, B, C on PE0, PE1, PE2.

All compiler manifests must pass complete round-trip revalidation. The frozen
PE admission report's cross-PE *edge occurrences* must agree with the
independent static projection; duplicate parallel edges must not disappear.
Each manifest is executed by the frozen Network via the versioned 24t host,
checked against the primitive 24n oracle on the original source program.
A second pure audit classifies every observed logical route occurrence as
local or remote without changing its timestamp, channel or multiplicity.

No silent admission skips are accepted: 216 x 3 = 648 compiled runs mandatory.

## Invariants

1. Total one-to-one node-to-PE ownership; PE identifiers never identify nodes.
2. P immutable program / S per-neuron state / E logical routed occurrence /
   O passive observation are retained as separate **logical** domains.
3. Static route edge multiplicity and dynamic observed route multiplicity
   are conserved, including duplicate parallel routes.
4. Frozen Compiler independently checks placement against capacity.
5. Under ideal, contention-free resource assumptions, all three mappings
   produce identical canonical result state, emissions, batches and routes.
6. Manifest source pins and deterministic cross-process replay are mandatory.
7. Changing PE placement is not permitted to rewrite logical delays.

## Explicit non-claims

This **does not** implement an independent PE scheduler or neuron dispatch,
physical or logical inter-PE packet transport, resource arbitration,
backpressure, clock-to-event-time mapping, PE failure recovery, cache coherence,
learning, memory access authorization or distributed state ownership.
The 24t host continues executing the reference Network, independent of PE
placement. Thus A1a establishes a placement/admission/projection baseline,
**not** proof of the correctness of a future distributed execution engine.

The next substantial A1b milestone is PE-local execution plus ideal inter-PE
transport with a second logical scheduler, compared against this baseline.
A2 Memory Fabric then adds the domain service and contention contracts.

## Gate

`bash search/spk_arch_a1_final_gate_v1a.sh`

Six stages: pure fabric contract, frozen integration, canonical process replay,
previous Compiler-host regression, full suite and tag/freeze/branch checks.
No tag or commit created automatically. No modifications to frozen modules.

## Engineering roadmap

The previous S1-S5 cycle ended at 94% (equal-weight engineering estimate) and
is now frozen as a **bounded reference profile**. A1-A5 starts at 0% pending
acceptance criteria; percentages are not mathematical correctness measures.

## Certified A1a gate

Frozen baseline: a76ebaae49373a4c6b66f94465d78dbf1cf19f80

- Pure PE placement tests: 12 PASS.
- Frozen Compiler/host integration tests: 7 PASS.
- Compiled placement executions: 648.
- Cross-PE route occurrences: 768.
- Previous Compiler/host regressions: 21 PASS.
- Complete repository regression: 3013 PASS.
- Cross-process evidence replay: PASS.
- Frozen source and patch hygiene: PASS.

Evidence SHA256:
3b650178521e2df512b5ebf86f8d49ae33ce6a4f96ff002ea3a7b8d6b515c5ee

Acceptance covers static placement and reference execution.
A1a does not implement PE-local computation or distributed scheduling.
