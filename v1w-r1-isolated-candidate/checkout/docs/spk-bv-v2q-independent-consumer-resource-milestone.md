# SPK Back Validation v2q — independently resource-charged actor consumer

## Research gate

`DERIVED_ACTOR_CONSUMER_INDEPENDENT_PE_MEMORY_CHARGED_NATIVE_PROJECTION`

v2p established ACK → distinct actor-applied credit without a separately
priced consumer operation. v2q adds a **second, independently booked derived
resource grant for each actual application**:

- A v2l ACK requires its prior independent receiver/resource custody.
- The actor application then reserves a **further 1 PE service unit and 2
  memory units** (one in O and one in E) against the *same source-pinned*
  global, per-PE and per-domain abstract budget.
- Only source-causally-serviced, actor-owned ACKs are eligible. Global FIFO
  prevents an available actor from bypassing an earlier unserviceable ACK.
- Resource pressure produces **pending applied-credit backlog**, not negative
  receiver judgment, negative certificate or counterfeit native learning.
- Native-tick grants mutate the resource counters in the separately compiled
  **derived executor**. Post-native consumer-only ticks become explicit paid
  rows on the **derived** resource timeline.
- Projection subtracts **only audited consumer charges**, then invokes
  inherited v2p/v2k journal/resource projection to reconstruct the complete
  untouched original native result. Unaccounted changes fail closed.

The unit costs are deliberately abstract proxies, **not measured hardware
cycles/energy/memory**. No source frozen scheduler/actor, Core, Network,
Algebra, Architecture or Compiler files have been modified.

## `fwork` reproduction

Retain the signed v2p report from the previously successful gate and install
only the eight newly added v2q research files:

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v2q_Independent_Consumer_Resource_Milestone.tar.gz

bash search/spk_bv_v2q_independent_consumer_resource_gate.sh \
  /tmp/spk-bv-v2p-actor-consumer-handoff.json \
  /tmp/spk-bv-v2q-independent-consumer-resource.json

bash search/spk_bv_v2q_inherited_regression_gate.sh
```

The predecessor is SHA-pinned, canonically validated and checked not to have
changed during replay. Report outputs must use a new, non-existing path
outside the repository; use a fresh filename for reruns.

## Verified local result

15 workloads × 3 native BV modes × 2 PE regimes = **90 independently
observed original-native full-result equalities**.

| Source PE budget | Native parity | ACKs | Independently paid applications | Extra PE | Extra memory | Charged inside native ticks | Paid tail turns |
|:--|--:|--:|--:|--:|--:|--:|--:|
| 3 slots/tick | 45/45 | 156 | 156 | 156 | 312 | 61 | 95 |
| 1 slot/tick | 45/45 | 156 | 156 | 156 | 312 | **0** | **156** |

Under a global 1-PE budget, all source-native tick capacity is occupied by
native work or earlier actor ACK service. The consumer therefore needs its
own fully accounted *post-native* tail. Across 45 contended cells the audit
detects 38 capacity rejections, with zero unaccounted spend.

45 further contended cells for each intervention:

| Intervention | Source ACKs | Independently paid applications | Pending backlog | Native equality |
|:--|--:|--:|--:|--:|
| Independent consumer total quota 1 | 156 | 45 | 111 | 45/45 |
| Consumer charge quota 0 | 156 | 0 | 156 | 45/45 |
| Resource-charge tail off | 156 | 0 | 156 | 45/45 |
| Consumer-specific memory allowance 0 | 156 | 0 | 156 | 45/45 |

The real source-B negative fixture produces exactly two delivered negative
judgments, two independently PE/memory-paid actor-A credit applications and
derived actor-A credit −2; frozen native learning remains absent.

Execution counts: 90 independent native originals, 90 normal paid consumer
replays, 180 resource/quota interventions and 2 negative-fixture runs.

- Local dedicated v2q unittest: **19/19 PASS**, including adversarial
  source budget drift, wrong actor/PE, rehashed forged charge, modified
  counters/tail rows, invalid plans and signed predecessor alterations.
- The user validated v2p milestone on `fwork`: **20/20 v2p**, **17/17 v2o**,
  **413/413** inherited pytest.
- Signed v2p canonical report SHA-256:
  `1c3f2b0010f6a0470ac2b5be021838b8e1992e85760e367a532d5e5dfe8f9ef3`.
- Local v2q canonical report SHA-256:
  `f214cbe1c75df7535171d14400c2cf37965fa5868aa55d02bc8a56f0891aa926`.

## Boundary and roadmap

Frozen native actor intake, independent *native* actor arbitration, learning,
physical consumer hardware cost and universal liveness remain **BLOCKED**.
The v2q proof is source-pinned and finite, not a generalized fairness theorem.

| SPK phase | Estimate | Delta since v2p | Gate / blocker |
|:--|--:|--:|:--|
| S1 | 100% | 0 | Frozen |
| S2 | 100% | 0 | Compiler conformance frozen |
| S3 | 60% | 0 | Back Validation research strengthens; native actor contract blocked |
| S4 | 0% | 0 | Not entered |
| S5 | 0% | 0 | Not entered |
| **Total (equal-weight average)** | **52%** | **0 pp** | No promotion from derived research |

Next candidate v2r: a **source-backed concurrent arbitration experiment**
between native forward work, receiver ACKs and independently paid consumer
work, with explicit contention counterexamples and conservation laws. No
change to the frozen native event-priority contract is assumed or authorized.
