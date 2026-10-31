# SPK Back Validation v4s-v4u — Paid derived actor ACK consumption (research)

## Scope and advance

In v4p-v4r, ACK transport competed with the native workload, but the derived
actor-local credit was updated at ACK arrival without another service grant.
In v4s-v4u, delivery **enqueues a pending judgment**. The derived consumer can
apply that judgment only on a separate successful resource admission:

- 1 owner-PE service grant on the same native clock;
- 1 owner-local **S** memory reservation on that tick;
- a receipt whose `consumer_tick` is not earlier than `delivery_tick`;
- a chained, source- and owner-bound derived actor credit update.

ACK send itself still consumes the v4m-v4o PE, O/E memory, shared/directional
link and in-flight resources. All competing forward/BV computations are actually
reexecuted, not statically relabeled. Frozen v0e and Architecture v1 unchanged.

## Five finite interventions on each of the 18 signed native recipes

| Variant | ACK origin/transport | Derived actor consumer | Distinct claim |
| --- | --- | --- | --- |
| `consumer_first` | Native-derived, resource charged | Before native service each tick | Prioritize actor credit at PE/S cost |
| `native_first` | Native-derived, resource charged | After forward and BV use remaining PE/S | Actor credits may wait |
| `consumer_disabled` | Native-derived, resource charged | No admission | Delivery is **not** credit |
| `feedback_disabled` | None | None | Exact frozen-native null parity |
| `zero_credit_policy` | Native-derived, resource charged | Policy-denied without service | Denial is not packet loss or negative opinion |

Observation from bounded signed source matrix: 18 original native replays,
90 derived reexecutions, 1,152 actual ACK transport deliveries and **576 paid
derived-actor consumption grants**. Under `native_first`, maximum observed wait
is 52 ticks; under `consumer_first` it is 0 on this finite workload. Native
forward traces differ causally from the frozen originals in 72 scenarios, while
null-feedback projection is exact in all 18 cases.

The **one-PE/one-S cost is a chosen abstract service model**, not a measured
implementation cost; the semantic judgment `+1` for receiver output and `-1`
for no output is likewise an explicit research policy, not general learning.

## Source custody and safeguards

- Signed source JSON `spk-bv-v3tuv-grant-rank.json` SHA-256
  `f783be9952613aa98eafef59d24c19eb64ccc09d29265017eabb675fe0155827`.
- Signed immediate predecessor `spk-bv-v4pqr-endogenous-actor-ACK.json`
  SHA-256 `9e33e4257cfb660861afcfb6f46efc6ee6893e78d060490faaefbd47d0dc5872`.
- The v4m parent module is checked byte-exact before compiling any transformed
  executable, and the CLI validates new modules and pinned native/actor code.
- Source grants, local PE/S memory, service timing, sign, actor ownership,
  ordered receipts, replay and chain hashes are independently audited.
- Create-only output; repository paths, stale outputs and symlinked inputs are
  rejected. Adversarial tests also reject missing service, forged ledger,
  wrong owner, time travel, mutated SHA and altered signed predecessor.

## Local gate

From the existing `spk-backvalidation-v0` checkout with v4p-v4r installed:

```bash
tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v4stu_Paid_Derived_Actor_ACK_Consumer_Research_Milestone.tar.gz

bash search/spk_bv_v4stu_paid_actor_consumer_gate.sh \
  ~/Scaricati/spk-bv-v3tuv-grant-rank.json \
  /tmp/spk-bv-v4jkl-shadow-arbiter.json \
  /tmp/spk-bv-v4mno-native-ACK-causal-replay.json \
  /tmp/spk-bv-v4pqr-endogenous-actor-ACK.json \
  /tmp/spk-bv-v4stu-paid-actor-consumer.json
```

Gate: v4stu new tests, v4pqr and v4mno inherited suites, native dual-priority
smoke execution, create-only signed report and byte-exact pinned observation.
`REJECTED` prints inside earlier adversarial tests are expected negative probes
when the enclosing unittest is `ok`.

## Deliberately excluded

No original native neuron's actor/consumer/learner is modified. No actual
weight/parameter update, promotion to Architecture v1, physical network
authentication, hardware cost evidence, or global liveness theorem is claimed.
Memory admission for credit-policy **evaluation** is not modeled: only a
successful derived credit consumption is charged. Credit denials remain
explicit rather than being misreported as negative evidence or lost ACKs.
