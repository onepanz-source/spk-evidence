# SPK Architecture v1: A2a P/S/E/O Memory Reservation & Trace Projection

**Status: INTEGRATION PASS (2026-10-16, bounded admission and trace domain).**

Baseline: SPK Simulator `spk-simulator-bounded-reference-v0`, commit
`a76ebaae49373a4c6b66f94465d78dbf1cf19f80`.

A1a places neurons, A1b executes on independent PE queues and states,
A1c accounts finite service slots, and A1d provides synchronous fail-stop
quiescence at a pre-grant boundary. A1d must be committed before this cycle.

## 1. Normative antecedents

This profile derives terminology and boundaries from existing contracts:
`docs/spk-memory-contract-v0.md`,
`docs/spk-memory-access-model-v0.md`, and
`docs/spk-memory-arbitration-v0.md`.
These older contracts distinguish logical intent from actual resource
transactions and EVENT_TIME from SERVICE_TIME. A2a does not replace the
existing `spk_architecture` v0 access authorization or PE admission contracts.

## 2. Four isolated logical domains

- **P:** active immutable program instructions, measured in instruction slots.
- **S:** independent per-neuron persistent state slots; guard is transient.
- **E:** bounded pending routed/initial event occurrences per PE, counted with
  multiplicity; output emission intent is recorded but output-buffer
  reservation is **not** modeled by this version.
- **O:** bounded records for observed batches and individual route occurrences.
  The observer record policy is fixed to the passive A1d trace.

These are explicitly **abstract units**, not bytes, cache lines or fetches.
Each PE has its own declared capacities. A batch causes a logical program
reference, state load, input consume, state commit, emission record per
emission, plus routing and observation intents. No memory bandwidth or
physical transaction count is inferred from these intents.

## 3. Pre-execution admission

`admit_memory_v1a` validates PE ownership from A1a and service constraints
from A1c, then conservatively reserves:

- P = number of active instructions placed on the PE;
- S = number of persistent states owned by the PE;
- E = at least the entire declared A1c per-PE event queue capacity;
- O = an upper bound on passive observation records per PE, derived from
  max_batches and the immutable CoreEmit/edge occurrences.

Insufficient or missing capacities, invalid identities and epochs fail
before A1d execution is called. The upper bound can reject a valid network
conservatively; such rejection is a resource admission decision, not a
semantic error. No candidate epoch activation or hot-swap is modeled.

## 4. Post-execution independent projection

`project_execution_memory_v1a` reconstructs E occupancy from the source
input events and ordered A1d committed batch/route occurrences. It never
silently deduplicates parallel edges or duplicate channel arrivals.

For every batch it checks that each consumed occurrence exists. For each
route it checks an admitted edge and positive logical delay, then credits
exactly one destination occurrence. A successful CLOSED run must leave no
pending events; a PE_FAULT run must reproduce the exact per-PE pending
occurrence counts in the preserved committed prefix.

Core result timestamps are never altered. The service ledger is observed,
not used to fabricate architectural memory transaction latency.
No new memory engine is invoked to compute neuronal states.

## 5. Source-pinned conformance

The immutable 216-case corpus is identified by SHA256
`cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`.

For `single`, `split`, and `spread` A1 placement:

1. Compile and run against the frozen host reference (648 comparisons).
2. Execute A1d nominally, assert exact canonical result equality.
3. Admit and project memory P/S/E/O, validate conservation and capacity.
4. Where a second committed batch exists, fail its PE before grant and
   validate the independent E and O committed-prefix projection (expected
   504 eligible failure prefixes).
5. Canonically seal the results; independently regenerate and verify the
   same SHA256 from separate Python processes.

A compiler reject, mismatch or missing eligible fault must fail the gate.

## 6. Explicit non-claims and next work

A2a is *memory ownership/resource reservation with a logical trace audit*.
It is **not** a banked memory emulator or runtime memory arbiter. In particular:

- No independent access-principal authentication/authorization (A2b).
- No bandwidth arbitration or per-domain SERVICE_TIME contention (A2c).
- No dynamic memory allocation, queue backpressure or NoC latency (A3).
- No output-buffer accounting or arbitrary observer isolation.
- No durable state, atomic rollback, candidate activation or PE recovery.
- No PE-local physical concurrency, caches or hardware assumptions.

A2 cannot be called complete after this cycle.

## 7. Final gate

`bash search/spk_arch_a2a_final_gate_v1a.sh`

Six stages: pure projection tests, frozen Compiler integration,
source-pinned independent-process replay, A1 regression, full repository
regression and frozen-boundary/whitespace checks. No Git commit or tag.

## Certified A2a gate

- Independent memory projection tests: 12 PASS.
- Real Compiler/host integration tests: 6 PASS.
- Compiled reference comparisons: 648.
- Projected fail-stop prefixes: 504.
- Cross-PE routed occurrences: 768.
- Previous A1 regressions: 37 PASS.
- Full repository regression: 3090 PASS.
- Independent-process evidence replay: PASS.
- Frozen-source and patch hygiene: PASS.

Evidence SHA256:
c7164a8abdf27e747f3522ec29b0449574aee219ab525b7f9cc1aff4acc80082

Acceptance covers P/S/E/O logical capacity, admission,
ownership and independently reconstructed access accounting.

No transaction authorization, physical memory transactions,
bandwidth arbitration, recovery or causal backpressure
is certified.
