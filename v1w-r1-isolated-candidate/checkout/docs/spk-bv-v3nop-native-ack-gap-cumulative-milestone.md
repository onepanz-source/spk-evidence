# SPK BV v3n–v3p: finite ACK readiness-to-grant gaps

Research-only derived actor queues on the source-compiled frozen native
scheduler. Core/Network, Compiler, Architecture and original native BV
are unchanged; the native executor has **no** actor-ACK or native learning
contract. An ACK eligible in the derived receiver is not a native actor ACK.

## Three cumulative steps

- **v3n — exact source tick partition.** For each replay, classify each
  source-native tick as ACK-not-ready, ready-and-granted, or ready-and-not-
  granted. Every missed ready tick is attributed to the actual frozen-native
  forward/BV priority veto, to the competing consumer-first queue selection,
  or to a resource-unproven ACK-first condition. Check conservation against
  original v3k resource and ACK journals. A native terminal cutoff is marked
  *censored*, never silence, dropped transport, or a negative judgment.
- **v3o — newly admitted source schedules.** Use three new eight-event
  arrangements, all accepted by frozen `actual_a3d_v0d` (maximum eight
  events, timestamps 1–32). Replay three native modes × PE slots {1,2},
  two derived queue policies × global ACK quotas {1,2}, with strict complete
  original-native projection and independent source-charged consumer/ACK
  receipts. Also replay zero-credit and receiver-loss causal nulls.
- **v3p — deadline discrimination and non-proof boundary.** Derive finite
  counterexamples to proposed short ACK-ready service deadlines from the
  exact gap traces; keep actor-specific or future scheduling guarantees
  explicitly unproved. Additional native input beyond the source fixture
  limit would be a *contract change*, not a valid research counterexample.

## Exact finite evidence

| Measured quantity | Source-replayed result |
| --- | ---: |
| New frozen original-native runs | 18 |
| Derived full-original-native parity runs | 72 / 72 |
| Causal nulls with no ACK or actor application | 36 / 36 |
| Derived runs with ≥8 consecutive ready/no-grant ticks | 66 / 72 |
| Derived runs with ≥16 consecutive ready/no-grant ticks | 53 / 72 |
| Derived runs with ≥32 consecutive ready/no-grant ticks | 24 / 72 |
| Longest consecutive ready/no-grant gap | 37 native ticks |
| Long gaps (≥16) that end in a real grant | 36 |
| Long gaps (≥16) censored at native horizon | 17 |
| Same-quota ACK-first inline ACKs not less than bounded-turns | 36 / 36 |
| Higher quota produced fewer inline ACKs | 3 / 36 |
| Higher quota worsened the longest ready/no-grant gap | 4 / 36 |

The longest **source-confirmed** gap is an eight-event admitted `eight_even`
workload, native BV `on_feedback_first`, **one** global PE slot,
`bounded-turns` policy, global ACK quota 2. A real ready ACK persists from
source tick 5 to tick 41, with **37 consecutive native-ready vetoes**; the
first next ACK grant occurs at tick 42. The receiver delivered 16 real
controls, 15 remained unapplied at the original native finish. This is a
counterexample to an unqualified 32-tick *readiness-to-service* deadline
within the admitted finite source domain. It is **not** a starvation trace.

Three additional source-backed quota reversals occur at two PE slots,
native `on_feedback_first`, policy `bounded-turns`:

- `eight_three_gap`: quota 1 admits 6 inline ACKs, quota 2 admits 4.
- `eight_clusters`: quota 1 admits 4 inline ACKs, quota 2 admits 3.
- `eight_even`: quota 1 admits 6 inline ACKs, quota 2 admits 5.

They join, but do not alter, the seven predecessor inversions. Even a larger
ACK quota can change queue history and subsequently increase the observed
readiness-to-grant gap; the source does not support monotone-delay promotion.

## What this does **not** prove

Each trace is finite, and this source fixture admits at most eight external
events in ticks 1–32. The audit never assumes unobserved post-native ACK
grants. There is no evidenced maximum interval between sufficiently resourced
native opportunities **for arbitrary future schedules**, and aggregate ACK
progress does not bound every actor's wait without a per-actor fairness
premise. Given only a finite prefix, both a future opportunity and the lack
of one remain logically compatible with the observations; this is an
*identifiability limitation*, not a claim that either infinite future is a
real frozen-native execution.

The next worthwhile contract-level question is an independently established
maximum-gap/rate assumption for native free opportunities, together with an
actor-specific queue-service fairness rule. Until then, universal native
ACK deadline, actor liveness and learning remain **BLOCKED**.

## Reproduce on `fwork`

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v3nop_Native_ACK_Gap_Cumulative_Milestone.tar.gz

bash search/spk_bv_v3nop_native_ack_gap_cumulative_gate.sh \
  /tmp/spk-bv-v3klm-native-ack-opportunity.json \
  /tmp/spk-bv-v3nop-native-ack-gap.json

bash search/spk_bv_v3nop_inherited_regression_gate.sh
```

Both reports are canonical, create-only and SHA-256 predecessor/source
pinned. Never overwrite the existing evidence: choose a fresh output
filename if the requested target already exists.

Roadmap checkpoint (equal-weight five-phase criterion): S1=100%, S2=100%,
S3=60%, S4=0%, S5=0%; total=52%, delta=0 percentage points. Finite
source-backed negative results are valuable but do not satisfy a frozen
native liveness acceptance criterion.
