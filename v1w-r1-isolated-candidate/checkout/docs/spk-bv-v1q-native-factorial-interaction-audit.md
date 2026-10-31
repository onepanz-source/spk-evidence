# SPK BV v1q | Bounded native full-factorial interaction audit

**Research-only.** Additive extension. No changes to frozen Core, Network, Compiler or Architecture v1. All operator replacements are exogenous, on detached native case copies before an episode. No reward, receiver-originated judgments, or neuron learning is claimed.

## Prior evidence and question

BV v1p on the frozen A→B→C fixture observed the following terminal emission counts after replacing `CMP(1)` by `CMP(2)` in exactly one node:

| Exogenous replacement | Terminal count | A→B occurrences | B→C occurrences |
|---|---:|---:|---:|
| none (sham) | 2 | 2 | 2 |
| A only | 0 | 0 | 0 |
| B only | 1 | 2 | 1 |
| C only | 1 | 2 | 2 |

These outcomes are confirmed by the uploaded **v1p native report**, not by test mocks. Merely adding singleton terminal deltas yields `2 - 2 - 1 - 1 = -2`, an impossible negative number of emitted terminal events. A correction for overlapping effects is therefore needed **before** treating count differences as decomposable. It is *not* evidence that native SPK has learned to assign credit.

## V1q factorial design

Run eight pre-episode program configurations: **none**, **A**, **B**, **C**, **AB**, **AC**, **BC**, **ABC**. The replaced operand for every included node is `CMP(1)→CMP(2)`; all other instructions, native external events, static fabric and resource plans are unchanged. Replay every configuration with BV **OFF** and **ON**, and **repeat each run once** to test exact deterministic replay. Thus the v1q matrix has **16 arm/mode results, from 32 scheduler calls**, in addition to the entire separately recomputed v1p ancestry.

### Mathematical representation

For a measured nonnegative event count `f(S)` with modified nodes `S` (subset of `{A,B,C}`), the finite inclusion-exclusion/Möbius coefficient is:

`I(S) = Σ_{T⊆S} (-1)^(|S|-|T|) f(T)`.

Examples:

- `I(A) = f(A) - f(∅)`
- `I(AB) = f(AB) - f(A) - f(B) + f(∅)`
- `I(ABC) = f(ABC) - f(AB) - f(AC) - f(BC) + f(A) + f(B) + f(C) - f(∅)`

The exact inverse reconstruction `f(S) = Σ_{T⊆S} I(T)` is checked. Signed coefficients are perfectly legitimate even though raw event counts are nonnegative. Coefficients describe **interaction on an explicitly chosen count statistic in this bounded experimental design**, not neuron causal credit, normative utility, or credit assigned from feedback.

Record coefficients separately for: terminal events, A→B deliveries, B→C deliveries, and native feedback assessment counts. **Do not sum** different metrics or promote feedback quantity to scored judgments.

## Source and safety gate

1. Require canonical v1p byte content, exact status, previously attested repetition, immutable native source provenance, known singleton outcomes and zero native judgments, operator commits and learning.
2. Re-run the **complete v1p CLI** against all preceding pinned JSON reports, requiring byte-for-byte identical output, before creating a new native claim.
3. Check identical frozen native fixture and source snapshots, and all native program SHA identities. Mutate only the specifically named node instructions using detached dataclass replacements. No original object, fabric, event or plan mutation is permitted.
4. For the **four singleton/sham combinations**, require equality of full native run summaries and whole-result SHA-256 with v1p, for both ON and OFF. Reconcile native emission/route/occurrence/ingress counts via the inherited v1p/v1m validators.
5. Validate counterfactual **upstream-prefix invariance** on every relevant factorial pair: adding B must not change A outputs or A→B deliveries, and adding C must not change A/B outputs or either incoming link. Require 16 pair/mode negative controls. These are fixture-specific, not a universal theorem of arbitrary SPK networks.
6. Require BV ON/OFF equality of the forward trace for each combination and no feedback under OFF. Nonzero ON feedback assessments remain unscored scheduler assessments, not neuron-produced preference evaluations.
7. For each count metric, use full eight-arm nonnegative integer observations. Enforce exact inclusion-exclusion and reconstruction; never invent multi-neuron effects from singleton runs.
8. All report inputs must be regular bounded files outside the working checkout, not symlinks, inode aliases, or paths reused as the output. Output path must not exist. Refuse source mutation, nondeterministic replay, missing reports, or architecture hash drift.

## Limits

The controlled interventions belong to the **experimenter**, not to the neurons. The scheduler's trace contains information the receiver **does not natively receive**. Full factorial event-count interactions identify neither a natural causal history for a silent spike, nor a utility objective, nor a judged benefit, nor a safe algebraic replacement, nor learning or rollback. Multi-episode holdout, endogenous value criteria, decision/absence witnesses and receiver-readable authenticated evidence are outside v1q.

## Running

After applying this incremental archive, run the isolated-import test gate:

```bash
bash search/spk_bv_v1q_research_gate.sh
```

For source-bound native evidence use `python -m search.spk_bv_v1q_native_factorial_interactions` with `--v1p` and **all v1p predecessor report paths**, plus `--out`, following the usual source-pinning and new-output-path rules. The native scheduler source is available on **fwork**, not in the temporary assistant checkout. The local tests exercise contract logic with explicitly synthetic fixtures and cannot certify results for compound interventions.
