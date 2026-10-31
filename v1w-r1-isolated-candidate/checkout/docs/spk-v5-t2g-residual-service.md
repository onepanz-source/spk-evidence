# SPK/* V5-T2g — Source-grounded residual-capacity shadow service

**Scope (21 October 2026): bounded research, no native scheduler modification, no native learning.**

## Scientific question

Can a T2f decision witness, including one for an explicitly silent decision, receive a semantic island judgment without pretending that BV v0e's already-consumed PE, memory and link services are free? What happens when the decision route collides with recorded native source work or misses an episode deadline?

## Exact construction and limitations

1. Run the unchanged original `spk_backvalidation_v0.live_dual_scheduler_v0e.execute_live_v0e` on the actual three-node episode and actual C demand condition (including no sensor). Preserve the original native resource timeline and output digest.
2. Separately replay frozen A1b to obtain the existing T2f *shadow-host-minted* decision witness and C closure. Compare native C forward arrival, C observed sensor channel, and closure tick to A1b. **If different, abstain**, not negative credit.
3. Schedule seven control stages in a **separate, post hoc residual-capacity shadow arbiter**, constrained by reported source PE/link/memory occupancy. Each stage has an owner PE, local memory domain, positive service cost and minimum causal tick. The same tick cannot be shared by consecutive control stages; the closure stage cannot precede C's source-executed closure. Native traffic always has first claim to its recorded resources.
4. Validate the **entire original BV v0e trace** against asserted capacity, not just sampled service ticks. Source profiles that cannot admit that trace are *refused* rather than retroactively shrinking native reservations. Memory after the last recorded native tick is conservatively treated as still reserving the peak per-PE/per-domain demand.
5. The finite horizon, missing shadow quota or transient link contention can leave a stage **pending**. This is never negative semantic credit. A deliberately lost route is **transport_loss**, not a negative judgment. An absent C sensor is **abstain_delivered** only if a return route completes.
6. `verify_residual_execution` separately reexecutes the original source and the research arbiter, defeating manipulated timestamps, owner assignments, reward bits and accounting sums. It is reproducibility custody, **not** independent authentication.

These shadow reservations are *hypothetical grants after reading source occupancy*, **not grants issued by the frozen BV scheduler**. The external T2f decision token is **not** an emitted or authenticated native event. This test cannot prove actual dual-traffic interleaving, full runtime noninterference, native service rates, multi-island fairness, or hardware costs. Correctness of synthetic demand labels is not independently established.

## Finite matrix and findings

Seven predeclared source-engine templates, one selected program per episode, five counterfactual resource profiles = **35 attempted cells**. All five replay the same explicitly versioned source logic. The profiles are independent counterfactuals, not 35 real-time concurrent episodes.

| Profile | Reward delivered | Abstain delivered | Pending deadline | Transport loss | Native-profile refusal |
| --- | ---: | ---: | ---: | ---: | ---: |
| Normal (PE fabric 4, link 1) | 5 | 2 | 0 | 0 | 0 |
| Tight PE (fabric 2, PE 2) | 5 | 2 | 0 | 0 | 0 |
| Deadline at start+9 | 3 | 2 | 2 | 0 | 0 |
| No links (original native source must first fit) | 0 | 0 | 5 | 0 | 2 |
| Reverse link deliberately lost | 0 | 0 | 0 | 7 | 0 |

Normal: 49 model shadow PE units, 84 memory units, 28 link grants, plus 5 observed link-busy deferrals; tight: 3 PE-busy and 5 link-busy deferrals. Native totals are **already occupied source loads**, not part of these new shadow charge sums. All full-delivery control packets have the T2f charge 7 PE / 12 memory / 4 link units each. The result includes two negative rewards for explicitly silent actions, but only because C's independent-from-action synthetic demand sensor generated a corresponding true request.

The no-link profile intentionally rejects episodes where original native activity itself uses links, rather than silently altering the source trace. The remaining silent episodes have no source links but still cannot transmit the extra semantic control.

## Gates and non-promotions

- 49 new adversarial tests plus inherited T2f/T2e/T2d/T2c/T2b/T1/T2 and native v0e/A1b tests.
- Frozen source and cumulative test/fixture pins SHA-256, create-only observation output, exact canonical reference and clean-checkout replay.
- **Admitted finding:** source-grounded shadow residual-service feasibility, nondelivery due to deadline and resource contention, authenticated only by replay of code, not by a trusted issuer.
- **Blocked:** interleaved native control service, native silent decision emission and native reverse semantic reward, true independent island goal evidence, independent held-out blind T3, native program updates.

**Next technically valuable question:** determine whether a *separately versioned, non-frozen experimental executor* can interleave and commit source and semantic-control resources in one actual scheduler run with explicit admissions, fairness and noninterference; otherwise the residual capacity simulation is only a conditional feasibility bound. Do not promote a protocol to frozen Architecture v1 based on this research-only replay.
