# SPK BV v4v-v4x — Feedback-conditioned computational candidate veto (research)

## Why this checkpoint matters

The earlier v4s-v4u milestone proved that a delivered ACK can be admitted and
charged to an actor-local credit consumer. It did **not** show that the feedback
semantics defines a safe learning objective, or that an actor possesses authority
to rewrite its frozen program. Here, a fully paid positive judgment may create
an *immutable research proposal* for the next episode, which is then separately
executed and audited. No original neuron code, instruction state, scheduler,
Architecture v1 contract or compiler output is altered in place.

The bounded hypothesis is to replace exactly one instruction operand in node
`A`: its `CMP` threshold is initially `1`, with candidate values `0`, `1`, `2`.
This is a **program-choice** experiment, not spike source weighting, Σ/σ
refactoring or gradient-based optimization.

## Two-episode boundary

1. Reexecute the source episode using the pinned v4stu paid actor consumer.
   Credit for node A is backed by actual receiver output, transported ACK,
   owner-PE/S consumption, and actor-local receipt chain. Require at least two
   paid positive judgments for A; one signed source recipe yields 8.
2. Form an immutable, owner-bound proposal with original/candidate program
   hashes, derived version `0 -> 1`, receipt root and receipt evidence digest.
3. Independently execute candidate instructions as **input to the frozen native
   executor** in a separate episode. Check exact forward/BV/actor equivalence
   on the signed recipe and a legal off-matrix channel-1 challenge.
4. Evaluate authority (owner + independent reviewer, research flags only),
   semantic preservation, holdout counterexample and no-op guards. A veto
   always leaves committed derived program version at 0.

## The finite matrix

| Candidate experiment | Change | Finding | Gate verdict |
| --- | --- | --- | --- |
| `owner_denied` | CMP 1 -> 0 | Owner has not authorized | VETO_AUTHORITY |
| `reviewer_denied` | CMP 1 -> 0 | Independent review absent | VETO_AUTHORITY |
| `signed_unsafe` | CMP 1 -> 2 | Native signed forward outputs diverge | VETO_SIGNED_SOURCE_SEMANTICS |
| `holdout_unsafe` | CMP 1 -> 0 | Signed outputs match, unseen channel-1 output diverges | VETO_OFF_MATRIX_COUNTEREXAMPLE |
| `no_op` | CMP 1 -> 1 | Behavior matches, program was not changed | VETO_NO_OP_NOT_LEARNING |

Across **18 source native workloads**, there are **18 resource-paid source
actor reexecutions** plus **90 separate candidate shadow episodes**. All 90
candidate promotions are rejected: 36 lacking authority, 18 signed divergence,
18 off-matrix counterexample and 18 no-op. Of 90 candidates, 72 show signed
source parity, but only the 18 true no-ops pass the deliberately chosen holdout.
This is empirical evidence, not a global semantic theorem.

Especially important: `CMP 1 -> 0` preserves the signed recipes because they
use input channel 0 and produce positive source evidence. Changing the first
external event's channel to `1` makes the original and candidate neurons
produce **different terminal emissions**. Thus an ACK credit and an observed
pass on the training recipes are not a general proof of a beneficial update.

The owner/reviewer Boolean flags encode *research authority hypotheses*, not
authenticated identities or real privileges. This gate intentionally cannot
promote any native learning change without a future explicit authority and
learning-objective contract.

## Local gate on fwork

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v4vwx_Actor_Candidate_Authority_Veto_Research_Milestone.tar.gz

bash search/spk_bv_v4vwx_candidate_authority_gate.sh \
  ~/Scaricati/spk-bv-v3tuv-grant-rank.json \
  /tmp/spk-bv-v4jkl-shadow-arbiter.json \
  /tmp/spk-bv-v4mno-native-ACK-causal-replay.json \
  /tmp/spk-bv-v4pqr-endogenous-actor-ACK.json \
  /tmp/spk-bv-v4stu-paid-actor-consumer.json \
  /tmp/spk-bv-v4vwx-candidate-authority.json
```

The cumulative gate comprises 18 new adversarial tests, 21 inherited v4stu,
18 v4pqr, 15 v4mno, frozen v0e dual scheduler smoke, create-only pinned
source report and byte-exact observation comparison.

## Excluded claims

- Zero native learning updates, zero derived algorithm promotions.
- No proof of global safety, optimality, model improvement, or hardware cost.
- No cryptographic authentication, remote peer trust or distributed authority.
- No arbitrary-topology semantics, source identity weights or coupled Σ/σ
  modification. These remain explicitly out of scope.

Next substantive requirement is to define a formal learning *objective*,
validation evidence and owner/reviewer authority which cannot be inferred
merely from reward-like ACK sign.
