# SPK Back Validation v1r: Posthoc Factorial Allocation Non-identifiability

## Scope

**Research-only additive code.** This experiment reuses the **source-bound frozen native scheduler** factorial outcome table obtained in v1q for the fixed A→B→C fixture. It DOES NOT install a native observer or side channel, select or update an operator using feedback, transmit a judgment, or change Core, Network, Compiler or Architecture v1. It DOES NOT certify an algebraic rewrite, usefulness, learning, or causal credit.

The actual v1q matrix has 8 interventions (`none`, `A`, `B`, `C`, `AB`, `AC`, `BC`, `ABC`) times BV OFF/ON (16 results), all imposed by an external experimenter on detached copies, never by the neurons. All three modifications are `CMP(1) → CMP(2)`. Interventions are **not** a temporal learning sequence.

## Main result: interactions defeat naive sums

For native terminal emission counts (both OFF and ON):

| Changed operators | none | A | B | C | AB | AC | BC | ABC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Terminal emissions | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 |

Summing isolated count changes gives `-2 -1 -1 = -4`. The complete intervention changes terminal emissions by only `0 - 2 = -2`. The Möbius terms from v1q restore exact counting: `AB=+1` and `AC=+1`; `BC=ABC=0`. These coefficients **describe overlapping effects in this fixed distribution**.

## A declared arithmetic allocation (not neuron credit)

v1r studies two **experimenter-imposed scoring polarities**, neither a neuron-supplied objective:

* `preserve_activity`: score is the terminal count.
* `suppress_activity`: score is minus the terminal count.

For each of six permutations of A/B/C, v1r lists successive *counterfactual* marginal score differences. Each ordering telescopes exactly to the same observed full-coalition score change, but individual marginals depend on ordering. For `suppress_activity`:

* `ABC`: A=2, B=0, C=0;
* `BCA`: A=0, B=1, C=1.

A purely descriptive allocation may average all six orders (equal-permutation average, often called a Shapley-style allocation). Exact rational arithmetic yields A=1, B=1/2, C=1/2, sum=2. The opposite polarity yields A=-1, B=-1/2, C=-1/2. Neither is ground truth utility, actionable BV credit or a neuronal decision signal: its value depends on a **chosen allocation convention, a chosen count metric, and a chosen objective polarity**.

Changing the observed metric also changes allocations, even with identical native runs. Under the same `suppress_activity` polarity:

| Count metric | A | B | C |
|---|---:|---:|---:|
| Terminal | 1 | 1/2 | 1/2 |
| A→B deliveries | 2 | 0 | 0 |
| B→C deliveries | 3/2 | 1/2 | 0 |

With BV ON, native feedback **assessment counts** happen to have the same count table as terminal emissions in this fixture. Assessment occurrence counts are not scored feedback or independent votes.

## Authority and epistemic limitation

1. All factorial outcomes and ordering marginals are accessible to the *experimenter* through native scheduler replay and posthoc logs, not to B/C through SPK messages.
2. The orderings are arithmetic routes across the static factorial table; they are **not** sequential runtime modifications, learned updates, or a feedback-driven controller.
3. `equal_permutation_average` is a declared choice of how to allocate count effects. It is not proof of causal credit in SPK's learning sense.
4. Count reduction may harm or benefit an externally defined objective; v1d and v1i already demonstrated objective polarity.
5. No native absence witness, producer-authenticated decision disclosure, receiver scoring oracle, commit, rollback or learning is present.

The prerequisite for attribution of **BV credit** is still a receiver-accessible, appropriately authenticated basis for judging the consequence of a particular sender decision, together with a justified objective and credit protocol. v1r does not supply those facilities.

## Source-bound CLI

`search/spk_bv_v1r_allocation_boundary.py` requires `--v1q` plus all source arguments inherited by the v1q CLI, and `--out`. It first checks canonical v1q bytes and internal factorial/count reconciliation; next it invokes the v1q CLI on the unchanged original source artifacts in a temporary location and requires the resulting bytes to equal the supplied v1q bytes. **Only after that** does it generate the v1r report and mark `native_v1q_recomputation_verified_in_this_run=true`.

The pure `spk_bv_research.native_allocation_boundary_v1r.analyze` function can check a supplied canonical v1q report and return an audit, but always leaves native recomputation attestation FALSE. Consequently, a report-only preview is not a new native experiment.

The CLI rejects symlinks/aliases, repository-internal input/output paths, oversized inputs, existing outputs, missing sources, altered predecessor bytes, modified source files during execution, false authority fields, tampered result counts, coefficient inconsistency and incomplete/intervention-incoherent matrices. It does not edit frozen native sources.

## Gates

1. `bash search/spk_bv_v1r_research_gate.sh` runs v1r tests, bytecode compile and the inherited v1q/frozen custody gate.
2. Run the source-bound v1r CLI separately on fwork; the gate script alone does not re-execute the native matrix.
3. Compare the v1r report with the optional report-only preview. Do not promote local preview output to native evidence.

This is a **stop-condition analysis**: factorial count effects are identifiable experimentally; a unique, receiver-legitimate valuation/credit signal is not identified from those counts alone.
