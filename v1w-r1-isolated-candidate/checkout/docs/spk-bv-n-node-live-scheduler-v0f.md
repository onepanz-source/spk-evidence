# SPK BV v0f — N-node live dual-event research executor

**Status: RESEARCH CANDIDATE.** Not an Architecture v1 replacement, a conforming hardware implementation, general-purpose SPK ISA, nor learning.

## Baseline custody

The authoritative frozen Architecture v1 tag is `spk-architecture-bounded-reference-v1`, commit `5af99cd1f4d603bf0c8e1557a6561c107765fdb5`. Its A1a/A1b/A3d three-neuron contracts and all other frozen modules remain unchanged. BV v0f lives exclusively under `spk_backvalidation_v0/` and `search/`, with independent tests under `tests/`.

## Research question

Can a parameterized population of neurons and processing elements execute the frozen A1 instruction fragment with a common logical spike/BV scheduling loop, maintain causal provenance, and reproduce the independent Network oracle **when service and links are uncongested**, without falsely treating two feedback paths as independent votes?

## Contract

- `layered_case_v0f((n0, n1, ...))` constructs a deterministic adjacent-layer graph over `N=sum(ni)` neurons, with positive route delays. Optional `recurrent=True` adds a **quiet feedback route** that is structural but does not loop indefinitely; it does not demonstrate plasticity.
- `plan_n_v0f(case, pe_count, mapping=None)` creates a *new research* `FabricV1a` container for any admitted N and M within explicit prototype quotas. Default mapping is round-robin, but a caller can provide one complete explicit mapping. The topology and the PE mapping are distinct. Identical parallel edges remain distinct, never collapsed.
- `_admit_n_v0f` validates node identities, program operands, state widths, routing occurrence multiplicity, timing, and PE ownership independently of frozen A1a `_admit`. It accepts only the frozen A1b instruction fragment `ACC`, `CMP`, `EMIT`, `RESET`, `SHIFT`.
- `execute_n_v0f` owns a state per neuron, pending input batches, cross-PE outboxes, causally timestamped spike occurrences, feedback packets, and shared PE/link/memory service quotas. Configured terminal assessor(s) may generate feedback along *actually delivered* causal parents; credit is counted once per `(assessment, receiver)`, even if several provenance paths lead to the same receiver. No assignment of global causal merit is claimed.
- Unlike v0e, neurons sharing one PE are not automatically suspended while an unrelated outgoing link waits: capacity applies to **the total current outbox occupancy plus the proposed batch**. A single impossible outbox burst fails explicitly; a temporarily full outbox defers its batch. This is a revised *research scheduling choice*, not a retroactive amendment to v0e or A3d.
- BV messages on the *same PE* consume logical service and two abstract memory units, but no cross-PE link grant. Cross-PE BV packets share link and in-flight quotas with forward spikes. All feedback is delayed at least one logical tick.
- `LiveBVPlanV0f(assessors=(...))` selects the observers explicitly: there is no hidden or default global evaluator. BV remains purely structural; **feedback does not change neuron programs**.
- Execution is bounded. This prototype explicitly limits admission to 1,024 neurons and 8,192 static edges, plus per-execution positive quotas. **These are experimental limits, not universal semantics**. A quota/horizon failure is not a completed computation.

## Evidence and limits

1. BV-disabled **uncongested** executions are checked against the independent primitive-oracle `search/spk_24n_independent_oracle_v0.py`: 10 parameterized layer shapes, three PE populations per shape, and 25 seeded acyclic graphs with varied PE assignments. Up to 64 neurons in the layered tests, with 128 possible in declared research admission bounds (not a performance benchmark). This is finite differential coverage, not a proof of universal equivalence.
2. Same-PE, mixed and distributed 4-neuron chains return three feedback judgments, with exact local-vs-cross PE accounting. A structural feedback cycle that terminates preserves finite ancestry; a persistent cycle hits the explicit batch limit.
3. Under shared-link contention, identical 4-neuron programs with two input events yield terminal ticks `[5,7]` with forward-first or `[5,10]` with feedback-first. The difference is caused by **live arbitration**, not post-execution annotations.
4. The test suite rejects forged PE owners/routes, missing/duplicate assessors, parallel-route multiplicity loss, unbounded loops, invalid layer specification, exceeded quotas, a noncanonical evidence envelope, and fully rehashed fabricated evidence that fails an independently regenerated source replay.
5. Replay evidence is generated from execution of the actual research engine and is reverified in a second process, with the original frozen baseline pinned.

## Claims expressly excluded

- All-network equivalence to frozen A3d, which is intentionally three-node and has different memory/scheduling rules.
- Physically parallel or decentralized clocking, real transistor-level energy, deterministic fairness under arbitrary recurrent traffic, bounded worst-case runtime outside declared horizons.
- Incremental or autonomous learning, generation of novel programs, global causal credit, contextual interpretation of performance, or secure activation of a program candidate.
- GUI: layer sizes and owners are currently Python API parameters, *not a GUI application*.

## Reproduction on `fwork`

Inside the existing research worktree `~/workspace/spk-backvalidation-v0`:

```bash
source ~/workspace/spk-algebra/.venv/bin/activate
bash search/spk_bv_v0f_research_gate.sh
bash search/spk_bv_credit_v0a_full_regression.sh
```

The second command intentionally deselects exactly six inherited Architecture v1 Git release-custody checks hard-coded to branch `spk-architecture-v1`; those checks previously passed as part of the frozen release and are not rewritten in research.

## Next decision

Do **not** bolt on a GUI or label N-node support complete. First establish a stronger independent *event identity + causal influence* oracle for convergent and recurrent N-node traffic under capacity constraints, then study how a context-conditioned local assessment can become a controlled program candidate, with resource cost and global-negative controls. The GUI should consume this validated configuration and trace interface.
