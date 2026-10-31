# SPK Back Validation v3k–v3m: source-native ACK opportunity condition

Research-only, derived actor service. Frozen Core/Network, Architecture,
Compiler and native BV source are not modified. No native learning rule is
inferred, and no universal native scheduler service deadline is established.

## Three cumulative research steps

- **v3k — source opportunity classification.** Replay pre-forward native
  readiness, queue selection and separately charged PE/RAM counters. An ACK
  ready tick without native work is *not* by itself a grant opportunity.
- **v3l — queue-policy discrimination.** Hold frozen source and native event
  result equal, while contrasting `ACK-first` versus `bounded-turns` with the
  actor-consumer queue present. Observe real ACKs and separately paid consumer
  receipts. Reject forgery, epoch reuse, fake resource grant and wrong clocks.
- **v3m — conditional resource progress and counterexamples.** Execute each
  source context with one or two global PE slots and one or two global ACK
  grants per tick. Require an actual ACK when *all* of these source-backed
  preconditions hold: delivered/due ACK ready, no native forward/BV veto,
  `ACK-first` selected, zero pre-forward PE/RAM baseline, source-owned
  admissible PE/memory capacities, and a positive resource quota. Record
  weaker-condition failures and any reversal when grant quotas increase.

## Pinned finite measurements

| Observable | Verified |
| --- | ---: |
| Frozen-original native contexts (9 schedules × 3 modes × 2 PE budgets) | 54 |
| Derived queue/PE/quota runs (54 × 2 policies × 2 quotas) | 216 |
| Zero-credit and transport-loss nulls | 108 |
| Strict, complete original-native projections | 216 + 108 |
| Strong conditional source opportunity with real ACK grant | 356 |
| Ready ACK, no native veto, but no ACK grant | 44 |
| Same-quota cases where ACK-first grants more inline than bounded-turns | 15 |
| Larger quota grants more inline | 31 |
| Larger quota grants **fewer** inline | **7** |

The seven reversals are source-backed counterexamples to the tempting but
invalid inference that increasing ACK service quota must monotonically
increase *native-phase* ACK count under the competing actor-consumer policy.
They are not proof of lost receiver judgments or negative feedback. Specific
schedule/policy/PE contexts and distinct ACK journal hashes are preserved in
the canonical JSON report. Increasing an instantaneous resource limit may
change earlier ACK/consumer queue choices and thereby later eligibility.

One concrete source replay is `three / on_feedback_first`, two PE slots,
`bounded-turns`: quota 1 ACKs at ticks 6, 7 and 13, while quota 2 ACKs twice
at tick 6. The second run subsequently chooses `consumer-first` at ticks 7
and 13, suppressing then-ready ACKs. This verifies the immediate queue-choice
mechanism **for that witness**; it does not prove it is the unique mechanism
for all seven inversions or for arbitrary future workloads.

The positive statement is conditional and local to actual source-derived
ticks. It does *not* supply a bound on when the frozen native scheduler next
leaves an ACK-eligible PE/RAM opportunity, and cannot imply unconditional
starvation freedom. A bounded gap between sufficiently equipped opportunities
would be an additional premise requiring independent evidence.

## Execute on `fwork`

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v3klm_Native_ACK_Opportunity_Cumulative_Milestone.tar.gz

bash search/spk_bv_v3klm_native_ack_opportunity_cumulative_gate.sh \
  /tmp/spk-bv-v3hij-ack-tail-opportunity.json \
  /tmp/spk-bv-v3klm-native-ack-opportunity.json

bash search/spk_bv_v3klm_inherited_regression_gate.sh
```

The report is create-only, canonical and SHA-256 pinned to the signed v3h–v3j
predecessor and all inherited source scripts. If the output already exists,
choose a *new* filename rather than overwriting historical evidence.

## Next scientific gate and roadmap

The next open question is a source-backed, independently justifiable **rate
or maximum-gap bound for native service opportunities** under explicitly
stated scheduler/load/resource assumptions. If native-forward or feedback
work can retain priority indefinitely, a finite ACK deadline remains blocked
even when every observed feasible opportunity is serviced correctly.

S1=100%, S2=100%, S3=60%, S4=0%, S5=0%: total=52%, Δ=0 points
under the established equal-weight criterion. Finite research milestones are
not percentages of a mathematical proof.
