# SPK BV v0g — causal closure, convergence and pressure (research)

**Status:** RESEARCH CANDIDATE; requires `fwork` gate. This does not amend the
frozen SPK Architecture v1 or any earlier BV research version.

## Question

Does the variable-N logical BV executor retain traceable causal provenance and
truthful shared-credit accounting under reconvergent paths, parallel edges,
cyclic topology and logical link contention?

## Implemented boundary

`audit_closed_v0g` is a separate **read-only checker** of the existing v0f
completed-trace output. It reconstructs: external event inputs and consumed
occurrences; one-to-one route multiplicities; source-batch parent references;
forward link grants; assessment terminal anchors; backward delivery along
actually observed forward edges; contextual feedback progression; per-assessment
receiver deduplication; and PE/link/memory accounting by logical tick.

It does **not** assume that consuming an occurrence implies that occurrence
counterfactually caused an output. A parent reference records membership in a
processed input batch. It does not prove neural attribution of merit.

The checker rejects any trace whose source-batch identity is ambiguous. In v0f
an occurrence records source neuron, emission tick and causal parent IDs, but
not a **unique service-batch ID**. If a neuron performs two distinct batches
at the same service tick, the checker does not claim to assign every emission
to a unique source batch. Its outcome is `BATCH_IDENTITY_AMBIGUITY` and must
not be counted as a successful closed-trace proof. The v0f runtime remains
untouched; the future runtime must carry source batch IDs end-to-end.

## Reproducible witness set

The independent-process evidence program captures ten source-backed scenarios:

1. Diamond convergence, one PE, and four PEs.
2. Diamond convergence with actual link contention under both priorities.
3. Deeper reconvergence under both priorities and bounded links.
4. A visited recurrence edge that becomes quiescent; no perpetual-completion claim.
5. Parallel route occurrences kept distinct, without vote amplification.
6. Layered 24- and 64-neuron high-fan-in research cases.

In uncongested scenarios the BV-disabled executor is additionally compared
with the independent frozen oracle's observable emissions and terminal outputs.
For a sustained recurrent loop, separate unit tests prove explicit batch-budget
rejection by both the v0f executor and the independent oracle.

The 64-neuron source case shows **528 BV packets**, **33 distinct (assessment,
receiver) pairs**, and **495 additional path receptions**. The 528 packets are
not 528 independent judgments; they are paid-for communication deliveries.
This is a cost/provenance observation, not a statistical estimate of value.

## Limits and next architectural consequence

- Read-only after-the-fact audit; does not upgrade the v0f scheduler itself.
- Global logical arbitration, atomic conservative memory credits, and finite
  research limits are retained.
- Timing under contention is intentionally not forced to match the ideal oracle.
- No learned program construction, merit validation, credit correctness,
  statistical generalization or physical energy measurement is claimed.
- **Next prerequisite before adapting programs:** stable occurrence **and
  source-batch IDs** at the N-node runtime boundary; then revisit how causal
  evidence is weighted or collapsed without discarding useful path diversity.

## `fwork` gate

```bash
cd ~/workspace/spk-backvalidation-v0
source ~/workspace/spk-algebra/.venv/bin/activate
tar -xzkf ~/Scaricati/SPK_BV_v0g_Causal_Stress.tar.gz
bash search/spk_bv_v0g_research_gate.sh
bash search/spk_bv_credit_v0a_full_regression.sh
```

The six architecture release-custody tests are deselected in the research
branch by the existing regression script; they remain frozen and unchanged.
