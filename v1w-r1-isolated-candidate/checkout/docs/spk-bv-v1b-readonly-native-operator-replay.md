# SPK/* BV v1b: Frozen native operator identification and readonly replay

**Research-only. No source modification, operator replacement, feedback judgment,
trained state, external truth, or architecture promotion.**

v1a proved only that a symbolic evaluator distinguishes improvement, degradation,
and ties on declared synthetic labels. The step toward actual SPK operators must
first discover which operations a frozen neuron actually executes, and prove
that a read-only replay agrees with the full frozen forward trace. This v1b probe
provides an *identity and execution witness*, not a learning experiment.

## Experiment and negative controls

- Accept a v1a toy audit and a v0w native report with verified SHA-256 linkage.
- Re-pin the three v0e native producer files to immutable v0t SHA-256 values;
  inspect the actual frozen `spk_architecture_v1/pe_execution_v1b.py` file,
  its SHA-256, and the AST of `_compute_local`.
- Execute the **existing** v0e native fixture once with BV **OFF**, forward-first,
  and exactly the original capacity and stimulus settings. Its complete result
  SHA-256 and forward metrics MUST equal the v0w OFF baseline.
- Reexecute each frozen forward batch individually using `_compute_local`,
  preserving the native input channels and state before each batch. Require
  exact raw-state/output agreement and deterministic duplicate evaluations.
- Verify fixture and node snapshots remain unchanged. Emit operator program
  fingerprints and typed instruction shapes for subsequent semantic research.
- No program edits, injected replacements, new labels, synthetic judgments,
  learned updates, holdout scores, or automatic operator promotion.
- The source fingerprint of `pe_execution_v1b.py` is **newly observed**, not
  historically pinned by v0w; don't claim a Git tag custody proof from SHA alone.
- No source code text is bundled with the report. The report describes local
  instruction shapes and microtraces only.

## Install

```bash
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v1b_Readonly_Native_Operator_Replay.tar.gz
bash search/spk_bv_v1b_research_gate.sh
```

## Actual native run (generates an output only when every assertion passes)

```bash
python -m search.spk_bv_v1b_native_operator_replay \
  --v1a /tmp/spk-bv-v1a-symbolic-holdout.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --out /tmp/spk-bv-v1b-native-operator-replay.json
```

The CLI refuses existing files or symlinked inputs/output and will not overwrite
an existing report. Run the full independent regression separately:

```bash
bash search/spk_bv_credit_v0a_full_regression.sh
```

**Promotion blocker:** v1b alone cannot judge whether a program instruction
substitution is admissible, nor prove benefit. A future experiment needs a
predeclared objective, a genuine native operator alternative, and paired next-
episode runs with an independent oracle and no mutable shared state.

## v1b.1 research-only hotfix: true native instruction representations

The original v1b program-shape reporter wrongly required each instruction to
be a Python dataclass. The native fixture codec permits multiple typed representations, and the
probe must not assume that every instruction is a dataclass. The hotfix derives
a bounded, lossless typed inventory via the existing `canonical_fixture` codec
already used for fixture SHA-256s. No new instruction validator is invented;
objects unsupported by the canonical codec and oversized programs remain rejected.
`operator_discriminants` reflect **syntax**, not certified operator semantics.
Source, fixture, OFF execution, microtrace, determinism, and mutation checks
are unchanged. Architecture v1, Core, Network and Compiler remain untouched.
An end-to-end run on the real fwork checkout is still required.
