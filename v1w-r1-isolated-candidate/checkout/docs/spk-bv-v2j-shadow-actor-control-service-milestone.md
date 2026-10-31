# SPK/* Back Validation v2j — Bounded shadow actor control service

## Decision

**Pinned derived research gate PASS; frozen native actor-service admission
BLOCKED.** No frozen Core, Network, Compiler, Architecture, v0e scheduler,
state or instruction set has been edited or implicitly promoted.

v2i proved that only 52 of 156 delivered controls were consumed when intake
was tied to the sender actor's *next forward batch*. v2j therefore tests an
independent control-service opportunity after the native scheduler completes
its work for each tick. A research-only, bounded ledger reserves leftover
**abstract** PE service and memory capacity without modifying the original
native grant counters. The shadow service is anchored after the native
`resource_timeline.append` at frozen v0e line 296; v2h's emission, ingress,
decision and clock anchors and v2g callsite wrappers remain inherited.

Source actor identity/owner PE come from the actual pinned `_admit` result.
Only delivered, due, receiver-authored, source-causally-owned judgments may
receive a shadow service grant. Every judgment is consumed at most once.

## Explicit research cost model

Each control-service receipt is assigned:

- **1** abstract PE service unit on the destination/sender actor's owner PE.
- **2** abstract local PE memory units: **1 O + 1 E** domain unit.
- At most **2** service receipts per tick, at most **1 per actor per tick**.
- An independently bounded maximum of **32 post-native shadow ticks**.

The cost weights are *chosen research proxies*, not proven native hardware
costs or an algebraic consequence. The simulation offers a receipt only when
the combined native usage plus its own shadow reservations stays within the
exact native plan's global, per-PE and memory-domain capacities. Every native
tick has a detailed audit row in the report. **Native resource counters are
never changed:** this is constrained shadow resource accounting, not an actual
PE grant transaction. A future integrated native control service could
change timing and forward results; v2j does not claim otherwise.

Native v0e stops when its original workload finishes. v2h may subsequently
drain remaining control packets. v2j can then execute separately labelled
`post-native-tail` research ticks with the same abstract capacity envelopes.
These shadow ticks are not frozen native logical ticks, and are not subject
to an established native actor control-service admission policy.

## Measured native-backed experiment, 15 workloads x 3 BV modes

| Measurement | Result |
|---|---:|
| Original native executions | 45 |
| Derived normal service executions | 45 |
| Derived loss, overflow, no-tail and tight-slot interventions | 180 |
| Additional native/derived real-negative-B runs | 2 |
| Total explicit runtime executions | **272** |
| Native/derived full-result parity | **45/45** |
| Feedback packets delivered to source-actor mailboxes | **156** |
| Shadow resource-charged service receipts | **156** |
| Receipts from residual capacity during original native ticks | 140 |
| Receipts in post-native shadow control ticks | 16 |
| Unconsumed delivered packets (normal shadow plan) | 0 |
| Shadow abstract PE service cost | 156 |
| Shadow abstract memory cost | 312 |
| Violated PE/global/domain resource envelopes | 0 |
| Original frozen actor state or resource counter updates | 0 |

The 16 tail receipts must not be confused with v2i's 15 *post-native
deliveries*. One additional control delivered earlier still required a later
shadow service opportunity. The report retains individual per-tick budget
audits so that this distinction is independently inspectable.

The negative-B fixture contains two genuine negative judgments issued by B.
Both are delivered and both obtain separately charged shadow service; A's
research ledger sums to -2. This is **not** learned credit, operator tuning,
state mutation or a claim about a globally beneficial decision.

Loss produces zero invented service receipts. Queue/mailbox overflow and
receipt/tail-pressure may leave controls unconsumed without turning silence
into negative evidence. Forged mailbox records, replay and wrong actor
ownership fail closed. The bounded, shadow-only interventions preserve the
original complete native result, including original timing and resource
timeline.

## Evidence and reproduction

- Pinned v2i predecessor SHA-256:
  `b09c0ceb778070f8dafa8913945ba952c497411b5cf9063ff6d8f9f0a7ff3010`.
- Native v0e SHA-256:
  `2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9`.
- Canonical v2j report SHA-256:
  `8fd1919c0bf197e83064828f074daa533038a1f798ea6398f8e0b88b0e6ae396`.
- Local v2j stdlib unittest: **13 tests PASS**.
- Full matrix with resource audit: **PASS** in the isolated preparation
  snapshot; report determinism can be checked by regenerating to a *new*
  file and comparing SHA-256.
- Inherited `pytest` regressions cannot execute in the preparation runtime
  (pytest not installed). On `fwork`, run the separate inherited gate; v2i
  had already passed 413 inherited regressions there.

Apply the strictly additive archive to the existing checkout:

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v2j_Shadow_Actor_Control_Service_Milestone.tar.gz

bash search/spk_bv_v2j_shadow_actor_control_service_gate.sh \
  /tmp/spk-bv-v2i-derived-actor-batch-intake.json \
  /tmp/spk-bv-v2j-shadow-actor-control-service.json

bash search/spk_bv_v2j_inherited_regression_gate.sh
```

The output must not already exist, and both input and output must lie outside
the repository. The input is byte-pinned, symlinks/source drift fail closed,
and all new files are separately versioned. For a repeat run, choose a fresh
output path; do not re-extract the same archive.

## Unresolved native admission gate

The next architectural step is to define and separately authorize a native
actor control-service admission and ownership contract, with chargeable real
PE/memory grants, independent wakeups, queue discipline, scheduling priority,
time horizons, resource starvation behavior and safe credit-consumption
semantics. Until that contract exists, neither native actor intake nor native
learning is proven or claimed. No cryptographic trust, distributed hardware,
N-node equivalence, rollback or cold promotion is established by v2j.
