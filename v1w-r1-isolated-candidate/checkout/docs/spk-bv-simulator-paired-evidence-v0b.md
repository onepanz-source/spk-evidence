# SPK Back Validation: simulator-backed paired evidence v0b

**Status:** research candidate. **NOT** a release, adaptation controller, causal-effect estimator, online BV transport, or statistical finding.

## Purpose and frozen dependencies

Move contextual-credit v0a beyond *invented numerical traces* by generating every execution witness from the frozen SPK Network v0 runtime and the independently implemented Architecture A1b PE-local engine. Two different programs execute against a reset state and exactly the same external event for each pair. Three static PE placement schemes (`single`, `split`, `spread`) must agree with the read-only Network v0 observer.

Frozen source tag: `spk-architecture-bounded-reference-v1`, commit `5af99cd1f4d603bf0c8e1557a6561c107765fdb5`. No changes to frozen modules or previous BV contracts.

## Concrete intervention

Three nodes `A`, `B`, `C`, with `A` forwarding channel 7 to both `B` and `C` after one tick, and B/C relaying each arrival to their terminal output. Each pair starts with **all states zero** and one external channel-0 event at `A`; the tick is 1..16. Only `A` changes.

Baseline program:

```text
ACC(1,0); SHIFT(1); CMP(1); EMIT(7); RESET(0)
```

Candidate program:

```text
SHIFT(1); ACC(1,0); CMP(1); EMIT(7); RESET(0)
```

The instruction **multiset is identical**, but the order of `SHIFT` and `ACC` changes. With events after tick zero, the baseline attenuates its newly accumulated unit before comparison, whereas the candidate attenuates before accumulating. Thus the same input produces zero terminal outputs in the baseline and two in the candidate. This is an *actual program-composition intervention*, but it is **manually constructed**, not autonomously invented.

## Contextual quality and the consensus trap

The task target is a **predeclared external label**, independent of local votes. For the beneficial context the target is two terminal spikes; for the consensus-trap context the target is zero terminal spikes. Global quality is a binary exact-match score, and local observation scores indicate whether each receiver B/C generated a terminal spike. This is a deliberately minimal toy task, not a cognitive or real-world benchmark.

| Context | Baseline terminal count | Candidate terminal count | Receiver preferences | Independent task verdict |
|---|---:|---:|---|---|
| `beneficial` (8 trials) | 0 | 2 | B and C favor candidate | Improvement, further verification only |
| `consensus-trap` (8 trials) | 0 | 2 | B and C favor candidate | Worse global objective, local/global conflict |

**The context, not a change in engine behavior, changes which program is desirable.** This demonstrates that local recipient satisfaction cannot stand in for task quality. It does not establish that local BV can autonomously infer the correct context label.

## Evidence and costs

The capture routine generates 16 pairs × 2 program arms × (1 Network v0 execution + 3 A1b PE layouts) = **128 real deterministic software executions**. For each arm, the complete frozen observable projection (emissions, terminal events, node states, observed batches/routes, event counts), three PE placement digests, program identity, reset state and input digests are reconstructed. A separate verify process reruns all engines and rejects a tampered witness even if someone recomputes its outer SHA-256 seal. The trust boundary is the checked-in research adapter and frozen Python source; this is not a cryptographic defense against malicious source changes.

Costs are **abstract counting proxies**, not joules or actual memory transactions:
- operations = sum of executed instruction counts over completed neuron batches;
- memory accesses = two conceptual accesses per completed batch;
- spike messages = number of routed edge occurrences;
- feedback messages = 0 because Network v0 does **not** physically execute BV messaging;
- candidate evaluation operations = 0 because the external research evaluator is not part of runtime; the full adaptation cost is **not accounted for**.

The last two zero fields must not be interpreted as evidence that back validation is free. They mark instrumentation that has not yet been implemented.

## Statistical limitation

The 16 cases are deliberately constructed deterministic fixtures, **not 16 independent draws from a population**. Variation in timestamp does not provide independent evidence of generalization. The inherited v0a sign-test diagnostic and threshold-based labels are run to verify software wiring only. **The nominal p-values have no inferential interpretation** and must not be presented as statistical significance. New tasks, genuine sampled variability, controlled randomized intervention, independently registered task metrics and comprehensive budget attribution are required before experimental claims.

## Structural limitations / next research questions

1. Only three neurons and simple fan-out; Architecture A1a still rejects N>3, and the structural v0 trace is not automatically constructed from PE occurrence IDs.
2. BV assessments are computed *post hoc* from Network observer traces. No real local feedback messages are propagated or charged.
3. External ground-truth context targets are supplied by experiment design. Context identification and merit inference by the network remain untested.
4. Program candidates are hand-authored and never staged or promoted. No local search, plasticity, or self-modification occurs.
5. No actual hardware concurrency, persistent queue recovery or energy metrics.
6. A genuine global-benefit estimator cannot be inferred from receiver consensus alone.

**Next step:** integrate occurrence-aware provenance and real, budgeted feedback propagation into a new research execution boundary, then test attribution against independent held-out objectives. Design scaling to N nodes around this mechanism rather than treating BV as an afterthought.

## fwork research gate

```bash
cd ~/workspace/spk-backvalidation-v0
source ~/workspace/spk-algebra/.venv/bin/activate
tar -xzkf ~/Scaricati/spk-bv-simulator-paired-evidence-v0b-research.tar.gz
bash search/spk_bv_v0b_research_gate.sh
bash search/spk_bv_credit_v0a_full_regression.sh
```

The six inherited tests tied to the frozen Architecture release branch remain explicitly deselected from the functional full-regression helper. They are neither edited nor considered passing on the research branch.
