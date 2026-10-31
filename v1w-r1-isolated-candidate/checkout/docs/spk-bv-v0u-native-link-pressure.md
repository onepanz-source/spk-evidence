# BV v0u: bounded link-pressure sensitivity (research only)

## Question

Does the forward-completion / feedback-wait tradeoff observed under `LiveBVPlanV0e` persist when **only abstract cross-PE link grant capacities change**?

## Method

Use exactly one invocation of pinned `search.spk_bv_v0e_live_evidence.fixture()` per process. For each of five explicit capacity cells `(fabric_slots_per_tick, link_slots_per_tick)`, re-run the three arms `OFF`, `ON forward-first`, `ON feedback-first`. All 15 native executions in a process receive identical network, stimulus, placement, temporal, service and memory plans; **only the link plan capacities are replaced between cells**, with a shared link plan *within* each cell. The original fixture is SHA-256 checked throughout.

Grid: `(1,1)`, `(2,1)`, `(2,2)`, `(4,1)`, `(4,2)`. The first cell *must* replay all 3 v0t runs including full-result hashes and the independently pinned v0o ON runs. Every cell separately measures resource totals, final terminal tick, feedback delivery completion and observational proxy nondominance.

Cells with unsupported native behaviors fail fast. No silent omission, no automatic selection of only successful conditions, no modification of v0e runtime. Execution is repeated in two separate Python processes with different hash seeds. Native source path and SHA-256 are verified before scheduler import and again after execution.

## Local frontier

The optional local nondominance report uses three **unequally-scaled, unweighted** proxy axes: last-terminal-tick penalty versus OFF, recorded `fabric_link` contention, and sum of *native-reported* feedback-grant waiting. It is explicitly NOT a physical optimum, a price/value ratio, or proof of informational advantage. No cross-cell Pareto ranking is claimed.

## Exclusions

No direct measure of benefit or learning because BV v0e does not adapt neuronal programs. No global causal credit, N-neuron scalability, power/latency inference, v0h 528-record equivalence, equal *effective* dynamic workload beyond fixed inputs, or promotion into frozen Architecture v1. The output only supports comparisons inside this bounded three-node source-pinned model.

## Commands

```bash
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/spk-bv-v0u-native-link-pressure-research.tar.gz
bash search/spk_bv_v0u_research_gate.sh
bash search/spk_bv_v0u_native_gate.sh /tmp/spk-bv-v0u-native /tmp/spk-bv-v0t-native-13.json
bash search/spk_bv_credit_v0a_full_regression.sh
```

Attach `/tmp/spk-bv-v0u-native-13.json` for analysis; the native gate itself compares it with the `-811` replay. New output paths must not exist already.
