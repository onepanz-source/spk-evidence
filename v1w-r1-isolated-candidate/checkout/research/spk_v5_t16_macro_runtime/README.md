# SPK V5 T16: staged causal learning in a versioned research runtime

This is ONE cumulative research macro-checkpoint building on T15 and the real
frozen PE primitive. It introduces durable distinct actor stages:

1. `C_PE`: read research-owned P and decide using original SPK `_compute_local`.
2. `WORLD`: simulated bounded thermal transition, independent of C's P state.
3. `A_PE`: compute difference with A-local pre-processing and frozen PE.
4. `B_RELAY`: PE computation and lineage-bound A verdict transport.
5. `C_CREDIT`: independent A/PE replay, validate B, CAS research-owned P.

Each **event dispatch is a separate atomic SQLite WAL transaction**. The
research owner C has a versioned P state, a single-use grant ledger, an SQL
write fence, permissions (`execute`/`verify`) and per-cell credit budget.
A budget/mode denial keeps C_CREDIT pending. Restarts resume without double
credit; identical-version concurrent feedback receives stale rejection.

## What this does NOT demonstrate

It does NOT adopt the frozen BV-v0e scheduler or its semantic-credit mechanism,
nor does it invoke the original T13 A1d access authorization on thermal P
writes. T13 original goals 11/12 are not the same semantic contract as T15
thermal setpoints 3..12, so claiming compatibility by relabeling is unsafe.
It does NOT integrate a real signed A sensor (T14), independent processes,
physical PE clocks, or independently measured physical causality. Host defines
worlds and can rewrite the research SQLite/database and program itself.

## Scientific result and parity

The gate uses the identical precommitted T15 split, controls and setpoints,
re-runs the original independent T15 research experiment and checks all five
condition totals, the reverse-actuator counterexample, and **60 individual
C decision sequences**. It explicitly reports positive OR negative findings.
Do not use 225 correlated evaluations as if they were 225 independent worlds.

## Execution on fwork (after extraction)

```bash
bash search/spk_v5_t16_macro_staged_learning_gate.sh \
  ~/workspace/spk-evidence/spk-v5-t16-macro-staged-learning.json
```

Uses a new output path (fails if already present) and leaves all original
components, freezes and existing T15 files unchanged. Never install a stub or
replace a frozen module to make an admission pass.
