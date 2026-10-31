# SPK BV v1p | Exogenous native causal-locus matrix

**Research-only, source-bound, hardware-independent.** No changes to frozen Architecture v1, Core, Network, Compiler or their contracts. Neither the sender nor a receiver learns or commits an operator. All interventions are created by the experimenter on detached copies **before** an episode.

## Motivation and scope

V1o demonstrates only that a hypothetical declared decision can be visible under stipulated disclosure assumptions; it does not identify why an emitted spike is missing. V1h and v1m offer a different, narrower source of evidence: the **experimenter** actually changes A's `CMP(1)` to `CMP(2)` and compares whole-fabric scheduler executions. This permits a bounded *interventional* contrast but not receiver-accessible knowledge, utility, or causal credit assigned by a neuron.

V1p locates that contrast in the **frozen, verified A→B→C feed-forward fixture** using three one-instruction copy replacements, plus a sham:

| Arm | Program modified | Instruction |
|---|---|---|
| `sham` | none (detached identical copy) | A `CMP(1)→CMP(1)` |
| `A_cmp2` | A only | A `CMP(1)→CMP(2)` |
| `B_cmp2` | B only | B `CMP(1)→CMP(2)` |
| `C_cmp2` | C only | C `CMP(1)→CMP(2)` |

Every arm is run in **BV OFF** and **BV ON**, with the original external events, unchanged other neurons, identical static routes and resource plans. Eight distinct arm/mode native runs are executed and **each is repeated once** to establish strict repeatability. The number of native execution calls in this module is therefore 16. The inherited v1o CLI also recomputes its own native ancestry separately.

## Validation contract

1. Fail closed on noncanonical source reports, mismatched SHA-256 references, source snapshots or fixture fingerprints. Re-run the complete v1o CLI and insist on byte-for-byte identity before any new claim.
2. Verify that every copied program differs in exactly one intended `CMP` operand; check program SHA and case identity, unchanged original objects, original events, fabric and plans. The sham remains semantically and structurally identical.
3. The original sham and A-intervention branches must reproduce all v1h OFF/ON forward summaries and whole-result hashes, not merely final spike counts. Native route, grant, occurrence and consumed-input accounting follows the already tested v1m `_extract` contract.
4. Check **prefix-invariance negative controls** on both modes: modifying B or C must not change A emissions or A→B deliveries; modifying C must not change B emissions or B→C deliveries. If this fails, the audit refuses to attest the feed-forward-localized result. This is a fixture-specific test, not a universal SPK theorem.
5. Check OFF/ON forward-summary equivalence and absence of feedback under OFF. All differences are represented as *directional count deltas*, not as evaluations of correctness, utility or preference.
6. Input files must be regular bounded files outside the checkout with no symlinks or inode aliases. Output must be a previously nonexistent path outside the checkout. No file may be overwritten. Any runtime or reference mismatch rejects the attestation without issuing a successful report.

## Scientific interpretation

A controlled exogenous change, coupled to the frozen deterministically replayed scheduler and identical nonintervened fixture, permits a **bounded experimenter-side interventional contrast**. If the result changes only downstream of the intervention in this fixed feed-forward test, this is evidence of locality *under the tested conditions*. It is not proof of general algebraic substitutability, a receiver-autonomous counterfactual, causal identification of why an arbitrary natural silence occurred, or benefit to any computational objective.

The three critical epistemic boundaries remain unchanged: the scheduler's producer-side trace is not a receiver-readable observation; a missing event without independently observed expectation/coverage is not a scored judgment; an experimenter-chosen pre-episode replacement is not an autonomous neuron update. No native absence certificate, authenticated decision record, endogenous judgment, learning or rollback is created.

## Reproducibility

Extract only the five additive source files. Run:

```
bash search/spk_bv_v1p_research_gate.sh
```

The test gate runs isolated-import v1p adversarial tests, compilation and the inherited v1o custody gate. A separate `search.spk_bv_v1p_native_causal_locus` CLI accepts `--v1o`, all v1o predecessor inputs, and `--out`. **The native CLI must run on fwork** (the assistant's temporary checkout lacks frozen Architecture v1). The local synthetic tests alone cannot attest native C/B responses.
