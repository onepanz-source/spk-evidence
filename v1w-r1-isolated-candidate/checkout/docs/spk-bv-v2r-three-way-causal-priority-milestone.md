# SPK Back Validation v2r — three-way causal guard discrimination

## Verdict

`DERIVED_THREE_WAY_CAUSAL_GUARD_CONTENTION_DISCRIMINATED_NATIVE_ARBITER_BLOCKED`

v2r tests how three resource/causality claims interact in a **separate
source-compiled research executor**:

1. causally ready frozen-native forward and BV feedback work;
2. delivered, resource-serviced actor feedback ACKs;
3. subsequent **independently PE/memory-paid** derived actor applications.

Four native-ready guard configurations are tested: both forward and BV
feedback protected; forward alone protected; BV feedback alone protected;
neither protected. This is a **source-backed differential discrimination**,
not an implementation or validation of the frozen native concurrent actor
arbiter. ACKs can contend *pre-forward* in the derived simulation. The v2q
consumer charge remains **post-forward per native tick**, so it cannot itself
preempt already-ready native forward work.

The frozen scheduler, actor, Core, Network, Architecture, Algebra and Compiler
are untouched. Every applied credit in each completed normal derived run
still commits its own independent 1-PE + 2-memory budget grant. Native
learning is not implemented or inferred.

## Reproduction on `fwork`

With the successful signed v2q report retained at its existing location:

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v2r_Three_Way_Causal_Priority_Milestone.tar.gz

bash search/spk_bv_v2r_three_way_causal_priority_gate.sh \
  /tmp/spk-bv-v2q-independent-consumer-resource.json \
  /tmp/spk-bv-v2r-three-way-causal-priority.json

bash search/spk_bv_v2r_inherited_regression_gate.sh
```

All seven v2r files are **additive**. The gate pins every inherited source
SHA, checks canonical signed v2q predecessor bytes and source AST anchors,
rejects a forged actor mailbox, and refuses existing/unsafe output paths.
When repeating a gate, choose a new output filename.

## Exact source-backed comparison

90 independently observed frozen native cells are matched against 360
derived runs (15 recipes × 3 BV modes × 2 PE capacities × 4 guard modes).

Full **entire-result** native parity, by source PE capacity:

| Native-ready protection | 3 PE/tick | 1 PE/tick |
|:--|--:|--:|
| Forward **and** feedback (strict) | **45/45** | **45/45** |
| Forward only | 45/45 | **15/45** |
| Feedback only | 40/45 | **0/45** |
| Neither (actor-first) | 38/45 | **0/45** |

For 1 PE/tick:

- Forward-only protection preserves the entire **forward trace 45/45**, but
  the native feedback trace matches only 15/45. Thus checking terminals or
  forward payload alone would miss the failure.
- Feedback-only protection changes the forward timing in **all 45 cells**;
  forward functional payload remains equal 45/45.
- Without either guard, full original native equality is **0/45** although
  all 45 functional payloads still match.
- In strict mode there are 156 ACKs and 156 independently paid consumer
  applications, all on consumer-only tail ticks under the 1-PE budget.

The resource/causal intervention matrix includes another **720 derived
runs**: four interventions for each of 180 contended guard-mode cells.

| Intervention | Source ACKs | Paid applications | Pending ACKs | Original native equality restored |
|:--|--:|--:|--:|--:|
| Consumer charge quota zero | 624 | 0 | 624 | 60/180 |
| Consumer tail disabled | 624 | 60 | 564 | 60/180 |
| Transport loss | 0 | 0 | 0 | **180/180** |
| Actor ACK credit policy zero | 0 | 0 | 0 | **180/180** |

This isolates the cause: **removing consumer service does not undo earlier
ACK priority contention**. Removing causal feedback from the consumer path
altogether (loss or admission refusal) restores the frozen-native output,
without a fabricated negative judgment.

The finite logical-horizon witness with `max_ticks=11` completes with exact
original-native projection only under the strict dual guard. All three
other guard configurations fail within the bound, with **no silence or
negative-evidence certificate**. This is a finite witnessed counterexample,
not a universal deadline theorem.

## Verification / scientific boundary

- Local adversarial v2r unittest: **17/17 PASS**.
- 90 independent native originals, 360 four-guard derived runs, 720
  resource/causal interventions, five horizon execution attempts.
- The signed v2q predecessor passed on `fwork`: **19/19** v2q, **20/20**
  v2p, **17/17** v2o and **413/413** inherited pytest.
- v2q canonical predecessor SHA-256:
  `f214cbe1c75df7535171d14400c2cf37965fa5868aa55d02bc8a56f0891aa926`.
- Local v2r report SHA-256:
  `731050ab7dc675b073afa9625b1cd378a9a4b7289e51d7f61078af294ba9f279`.

The next unresolved boundary is a **genuine simultaneous native-ready / ACK /
consumer pre-forward service arbitration** with explicit resource conservation
and either proof of a closed witness or a counterexample. The native event
priority contract, operator learning, general liveness and physical resource
cost remain **BLOCKED**.

| SPK phase | Progress estimate | Delta from v2q | Unresolved gate |
|:--|--:|--:|:--|
| S1 | 100% | 0 | Frozen |
| S2 | 100% | 0 | Compiler frozen |
| S3 | 60% | 0 | Native actor arbitration / learning still blocked |
| S4 | 0% | 0 | Not entered |
| S5 | 0% | 0 | Not entered |
| **Total (equal-weight mean)** | **52%** | **0 pp** | Research does not promote native contracts |
