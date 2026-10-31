# SPK Architecture v1: A1d PE Fail-Stop & Quiescent Prefix

**Status: INTEGRATION PASS (2026-10-16, synchronous pre-grant fault domain).**

Frozen reference: `spk-simulator-bounded-reference-v0`, target
`a76ebaae49373a4c6b66f94465d78dbf1cf19f80`.

Upstream A1a places and admits three-neuron graphs. A1b executes on PE-owned
queues and memories. A1c implements deterministic finite service capacities
on a clock separate from logical spike timestamps.

## Contract and fail-stop boundary

A1d adds an *actual stepwise fault-aware PE executor*, rather than computing
the complete result and truncating its trace. A test-specified PE fails at its
N-th *local batch*, after the global arbiter has selected that batch and after
budget checking, but **before its service grant, dequeue, state mutation or
spike production**. The synchronous reference fabric immediately quiesces.

The returned `PE_FAULT` witness includes the failed PE, logical head, exactly
committed batch and event counts, per-PE state snapshot, remaining queue
occurrences, emissions, routes and service ledger. It **does not** contain a
`CLOSED` result or success receipt. Already committed work is *not* rolled
back. An unreachable requested fault raises `PEFaultNotReachedV1d` rather
than treating the run as successful.

No-fault execution produces `CLOSED` and must match every field of A1c service
execution for the same case and service plan, as well as the A1b logical
result. The new PE engine executes the admitted instruction fragment itself
and does not import frozen Core, Compiler, Network, host or oracle.

## Independent source-pinned conformance

Pinned corpus of 216 DAGs:
`cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`.

For each case and `single`, `split`, `spread` placement, the integration
adapter verifies an independently compiled host reference. It then executes
A1d nominally under two service plans (one-slot shared/local, and
unconstrained), comparing the complete results with A1c and the frozen host.
For cases having at least two batches it also fails the owner of the second
batch, verifies **exactly one committed batch**, retains pending occurrences,
and compares the preserved prefix with the A1c nominal trace. No compiler
reject, missing trigger or divergence may be silently omitted from evidence.

Expected coverage: 648 compiled references; 1,296 nominal A1d service runs;
1,008 reachable two-batch PE failure injections in the declared corpus.
These counts must be confirmed by the authoritative gate, not presumed.

The canonical JSON evidence is verified with a source-pinned replay, a strict
hash, two independent Python processes and negative tests for forged evidence
with a recomputed hash.

## Explicit non-claims

- This is **synchronous reference-wide fail-stop**, not continued execution
  of healthy PEs, asynchronous failure detection or fault tolerance.
- No mid-batch crash, torn state write, durable checkpoint, replay or rollback.
- No watchdog, PE rehoming, distributed failure detector, quorum or consensus.
- No physical fault timing, independent PE clocks, NoC loss or backpressure.
- No proof that a real distributed platform can atomically quiesce all PEs.
- No general guarantee outside the pinned three-neuron instruction fragment.

## Final gate

`bash search/spk_arch_a1d_final_gate_v1d.sh`

Six stages: independent PE fault execution; frozen integration; two-process
replay; A1a/A1b/A1c regressions; entire repository suite; immutable frozen
tag and patch hygiene. No automatic Git commit or tag.

## Roadmap

Completes the fourth declared A1 PE Fabric criterion only when the complete
`fwork` gate passes, **in the limited synchronous fail-stop reference scope**.
A2 Memory Fabric and A3 causal timing / backpressure remain new work.

## Certified A1d gate

- Independent PE fail-stop tests: 14 PASS.
- Frozen Compiler/host integration: 7 PASS.
- Compiled reference comparisons: 648.
- Nominal service executions: 1296.
- Eligible fail-stop injections: 1008.
- Previous A1 regressions: 57 PASS.
- Full repository regression: 3072 PASS.
- Cross-process canonical replay: PASS.
- Frozen boundaries and patch hygiene: PASS.

Evidence SHA256:
96c36f0306c044dee5a73d7c5c372ac2569e99fb1428cd40f4e6075dd1a4104f

Acceptance covers synchronous, global quiescence
on a deterministic pre-service-grant PE failure.

No asynchronous fault detection, continued execution,
failover, rollback or durable recovery is certified.
