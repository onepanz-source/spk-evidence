# SPK BV v4y–v4aa — external task objective versus local actor ACK

Classification: **research only**, not a computational learner or an
extension of frozen Core/Compiler/Architecture v1. There is no native or
shadow program adoption in this milestone.

## Question

When the receiving neuron produces a positive ACK and the originating neuron
gets paid actor credit, is the original action necessarily useful? **No.**
The v0e three-node fixture admits a specific counterexample: when actor A's
`CMP` threshold is reduced from 1 to 0, channel 1 input (declared negative
by this synthetic task) still produces a terminal C emission. The real
receiving B neuron nonetheless executes and produces a positive paid ACK.

## Declared experimental task and loss

Single external event delivered to A, two classifications:

| A input | Desired terminal C emission count | Interpretation |
| --- | --- | --- |
| channel 0 | 1 | task-positive |
| channel 1 | 0 | task-negative/distractor |

The external test contract stipulates `loss = 5·FN + 4·FP`, with hard
componentwise non-regression and additional temporal challenge at event tick
`t+7`. This is a **chosen, synthetic hypothesis**, not an inferred domain
label, native task specification, unbiased holdout, or real-world oracle.

## Matrix, controls, and boundaries

- Preserve all 18 signed native runs, pinned by the v3tuv report; v4vwx is an
  exact signed predecessor as well. Run 7 derived cases against each source
  combination: 126 counterfactual objective trials.
- Signed source `CMP=1` already scores 0 under the selected task. `CMP=0`
  scores 4 (one FP) and `CMP=2` scores 5 (one FN): neither improves it.
- Artificially degrade a *separate shadow input* to `CMP=0` and propose
  restoring `CMP=1`. This supplies a falsifiable positive control: loss 4→0,
  with both componentwise and temporal checks. Its outcome is **eligibility
  for a future shadow trial only**, not a commit or native learner action.
- `CMP=0→2` is a negative tradeoff control, loss 4→5. Denial of either owner
  or independent review vetoes the positive repair. Both roles are boolean
  experiment flags; neither provides authentication.
- The negative-label overfire case generates one *genuine, transported and
  PE/S-service-paid* positive actor-A ACK. The ACK is causally valid as a
  receiving neuron's local response; it is **not an external task success**.
- The independent audit reexecutes the frozen v0e forward evaluator and paid
  ACK consumer, reconstructs the loss from declared labels, rechecks proposal
  identities, versions and digests, and fails closed on forged results.

## Out of scope

No authentic external oracle, learned objective, generalized task validity,
physical energy measurement, online program update, native learning, source
identity weights, mesh topology or hardware deployment. In particular, a
two-channel probe and shifted-tick replication are not an independent
distribution-shift validation.

Next research gate: source and authority of *task labels* and objective
provenance, including adversarial label-oracle compromise, before any program
promotion is contemplated.
