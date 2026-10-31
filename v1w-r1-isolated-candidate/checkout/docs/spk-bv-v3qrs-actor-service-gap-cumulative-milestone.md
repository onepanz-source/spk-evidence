# SPK BV v3q–v3s: source-owned actor ACK service gap

Research milestone; the frozen native scheduler, Core, Network, Compiler and
Architecture remain unchanged.  Native `execute_live_v0e` is never rebound.

## Research question

Do aggregate source-backed ACK grants imply progress for every receiver-owned
actor with control ready? **No**, even within the finite source-admitted
three-node experiment. Global queue progress is not an actor-local service
certificate. This finding does **not** prove permanent starvation.

### Cumulative stages

1. **v3q:** Replay delivered actor-addressed judgments and match each source
   emission, receiver, recipient, due tick and response to exactly one
   resource-charged ACK. Distinguish due within native execution from feedback
   delivered during explicit post-native drain.
2. **v3r:** Partition *each actor's* ready native tick into serviced, native
   priority veto, consumer reservation, peer actor granted, or source resource
   not independently certified. The same tick can advance global ACK count
   while leaving another ready actor unserved.
3. **v3s:** Replay three fresh eight-external-event schedules across original
   BV modes, native PE budgets 1/2, derived ACK-first/bounded-turn policies and
   quotas 1/2; prove strict original-native projection and causal-null closure.

### Source-backed results

| Measurement | Observed |
|:--|--:|
| New original native runs | 18 |
| Derived source actor-policy/capacity runs | 72 |
| Native-exact source projections | 72/72 |
| Causal nulls (`zero_credit`, `transport_loss`) | 36/36 |
| Source-delivered feedback, summed over 72 contexts | 1,152 |
| Source native-slack actor ACKs | 131 |
| Per-actor ready tick observations | 3,928 |
| Per-actor ready but unserviced ticks | 3,797 |
| Global-grant ticks with a waiting peer | **71** |
| Derived contexts with such a peer | **47/72** |
| Maximum observed single-actor service gap | 37 native ticks |
| Native-horizon unconsumed actor records, censored | 965 |
| Explicit post-native deliveries, not called native-ready | 56 |

*Representative counterexample:* new schedule `eight_split_burst`, native BV
`off`, PE budget 2, derived ACK-first and global quota 1: on source tick 13
both A and B have source-owned feedback ready; A is granted one genuine ACK
while B remains unserved. Therefore a service guarantee inferred from the
global ACK counter would be false for B.

The aggregate 3,928 ready actor-ticks obey `3,928 = 131 + 3,797` exactly.
The 965 censored actor records are pending at the original native horizon,
not negative judgments. The 56 post-native deliveries are distinct.

### Falsification controls

- Canonical SHA-256-pinned v3n–v3p predecessor and byte-pinned inherited/native
  source with last-byte recheck; reject altered report/status/claim/count.
- Replay source custody: wrong actor, stale/early ACK, mismatched source
  emission, duplicate ACK, duplicate judgment, altered delivery summary,
  forged after-native count all fail closed.
- 12 v3q–v3s dedicated adversarial unit tests and 72 native-exact derived
  replays; 36 causal-null executions mint no ACK or negative certificate.
- Only source-admitted fixture events (at most eight, external tick at most
  32) are used. A hypothetical ninth event is *not* labeled native.

### Limits / not proven

This is a finite source-derived control experiment; it neither implements
native actor intake nor establishes a native fair-service policy, upper bound
on future service gaps, universal liveness, per-actor learning, authenticity
of distributed actors or energy/hardware performance. Feedback remains
separate from frozen neuronal state, and source-address custody is not
cryptographic authentication.

The next *contractual* gate is blocked by the absent frozen-native per-actor
fair scheduler and minimum service-opportunity-rate specification. New
research must not silently promote derived fairness into that contract.

### Reproduction on `fwork`

```
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v3qrs_Actor_Service_Gap_Cumulative_Milestone.tar.gz

bash search/spk_bv_v3qrs_actor_service_gap_cumulative_gate.sh \
  /tmp/spk-bv-v3nop-native-ack-gap.json \
  /tmp/spk-bv-v3qrs-actor-service-gap.json

bash search/spk_bv_v3qrs_inherited_regression_gate.sh
```

Use an **unused** destination JSON. The gate creates it exclusively and rejects
overwrite; the intentional `REJECTED` lines inside adversarial tests are PASS
conditions when the enclosing unittest returns OK.

### Roadmap

| Simulator/Compiler phase | Progress | Since preceding checkpoint |
|:--|--:|--:|
| S1 | 100% | 0 pp |
| S2 | 100% | 0 pp |
| S3 | 60% | 0 pp |
| S4 | 0% | 0 pp |
| S5 | 0% | 0 pp |
| **Equal-weight total** | **52%** | **0 pp** |

No progress percentage changes from the existence of an additional finite
research witness; release acceptance criteria have not changed.
