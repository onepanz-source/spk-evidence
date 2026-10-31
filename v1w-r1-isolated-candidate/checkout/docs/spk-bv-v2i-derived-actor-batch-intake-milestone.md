# SPK/* Back Validation v2i — Derived committed actor-batch intake

## Decision

**Research gate PASS; frozen actor intake/learning promotion BLOCKED.**

The previously signed-off v2h actor-scoped mailbox now has a separate v2i
read-only *consumption ledger*. For each actual committed actor batch in an
in-memory derivative of the pinned `live_dual_scheduler_v0e.py`, the v2i proxy
offers previously delivered causal judgments to the identified actor. It
records bounded, idempotent `ActorReceiptV2i` records and a separate sum of
signed research credit. The frozen `_compute_local` program never reads this
credit. The frozen A3d, Core, Network, Compiler, Architecture, v0e scheduler,
and neuron states remain unmodified.

The source/actor admission comes from the native `_admit` return, not the
caller-provided label. Its hook is precisely the v2h pinned batch statement at
line 194, after the native batch is committed; `_compute_local` is pinned as
a single native call at line 183. The v2h emission/ingress/receiver proof and
the v2g callsite wrappers remain in force. v2i is an *in-process research
adapter*, not an actual frozen actor implementation or security boundary.

## Grounded evidence from 15 x 3 original native workloads

| Observable | Proven result |
|---|---:|
| Original frozen executions | 45 |
| New derived normal executions | 45 |
| Derived control-loss interventions | 45 |
| Derived one-receipt bounded-pressure interventions | 45 |
| Additional native/derived negative-B runs | 2 |
| Total explicit runtime executions | 182 |
| Full historical native result parity | 45/45 |
| Real committed actor-batch visits observed | 234 |
| Causal feedback packets delivered by v2h | 156 |
| **Derived actor-batch receipts actually consumed** | **52** |
| Delivered but not consumed in a later actor batch | 104 |
| Of those, delivered during native-loop ticks | 89 |
| Of those, delivered in post-native research drain | 15 |
| Native operator/learner state updates | 0 |

The 104 unconsumed messages are a genuine finding, not a test failure or an
implicit negative vote. In this runtime an actor computes only when forward
input is scheduled. Delivery to its mailbox does not trigger an independent
actor control-service event. Post-native drain expressly has no native actor
intake. The current resource model does not charge v2i for actor service or
memory grants. These are blockers for any native control-plane claim.

The adversarial negative-B fixture has two real receiver judgments of -1,
both delivered to sender A. One is consumed at a later A batch; one stays
unconsumed. The research ledger therefore observes A credit -1, not -2,
and asserts no absent event or learning effect. Loss yields zero receipts,
independent of the judgments the receiver originally made. Bounded receipt
storage pressure may defer consumption, but never mutates frozen forward
outputs or fabric resource accounting.

## Local evidence and release gates

- Pinned v2h input SHA-256:
  `8407d93d78ca1aba76b1b01e65bafc9692aa35715261b53833366823f37138cd`.
- Frozen native v0e SHA-256:
  `2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9`.
- v2i canonical report SHA-256:
  `b09c0ceb778070f8dafa8913945ba952c497411b5cf9063ff6d8f9f0a7ff3010`.
- 12 new stdlib unit tests **PASS** on the local isolated snapshot.
- The v2i native/derived matrix **PASS**, including report determinism,
  source custody, predecessor mutation rejection, cross-actor controls,
  replay, mailbox forgery, resource pressure and loss.
- Inherited `pytest` regressions cannot run in this preparation environment
  (pytest unavailable), so a separate selected regression gate is required
  on `fwork`. The previously returned v2h inherited gate had 413 PASS.

## Reproduction on `fwork`

Extract the additive v2i release at your existing checkout root. All files
are new, versioned paths. The extraction must not overwrite existing files.

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_BV_v2i_Derived_Actor_Batch_Intake_Milestone.tar.gz

bash search/spk_bv_v2i_actor_batch_intake_gate.sh \
  /tmp/spk-bv-v2h-derived-actor-feedback.json \
  /tmp/spk-bv-v2i-derived-actor-batch-intake.json

bash search/spk_bv_v2i_inherited_regression_gate.sh
```

The v2h predecessor must be canonical, byte-identical and of exact pinned
SHA. The v2i output must not exist before running. Inputs and outputs must
be outside the repository. The generator fails closed on source drift.

## Not yet established

No actor-native control event, isolated PE/VM inbox, ingress admission API,
control-service quota/latency/resource reservation, cryptographic origin,
transport reliability, offline-to-live learning equivalence, autonomous
credit-to-operator policy, commit/rollback rule, cold promotion, N-node or
hardware claim has been established. The next gate must define an explicit
actor-owned control-service contract with independently charged resources
before attempting any change to frozen behavior.
