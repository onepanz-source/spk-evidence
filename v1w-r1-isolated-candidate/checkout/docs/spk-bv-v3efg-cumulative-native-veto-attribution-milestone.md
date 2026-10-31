# SPK BV v3e–v3g — causal native-guard factorial, ACK wait accounting, no-tail boundary

Research-only derived actor. Frozen `live_dual_scheduler_v0e.py`, Core/Network,
Compiler and Architecture source and contracts remain unchanged.

## New source-backed experiments

* **v3e:** a genuine 2×2 factorial of source-native ready-forward vs ready-BV
  protection, with all three established ACK/consumer queue policies. Original
  2–8 external-episode schedules are augmented with three independent 8-event
  schedules (four-tick spacing, late events, paired bursts). Each native mode
  is independently executed on the unchanged signed source.
* **v3f:** every due-to-ACK-service waiting tick is classified *exactly once*
  as simultaneous native veto, forward-only veto, native-feedback-only veto,
  unblocked original native tick or post-native research tail. The auditor also
  checks actual pre-forward PE grants and source-owned queue probes. These
  are **observed overlaps**: they do not claim that every classified tick
  independently caused the delay.
* **v3g:** execute the source-derived actor with its real tail explicitly
  disabled; no pending feedback is forged into an ACK or negative judgment.
  Repeat source loss and zero-credit causal nulls; when no controls are
  admitted, the full native result is recovered.

## Pinned finite matrix

| Evidence | New source-backed observations |
| --- | ---: |
| Original native runs (nine schedules × three BV modes) | 27 |
| Derived queue runs (four guard modes × three queue policies) | 324 |
| Loss/zero-credit causal null runs | 54 |
| Tail-disabled derived runs | 27 |
| Per-policy strict-native full-projection equality | 27/27 |
| Functional forward payload equality | 324/324 |
| Cross-guard paired comparisons | 81 |
| Tail-off delivered controls still unACKed | 266 |
| Tail-off full native projections | 27/27 |

In the pinned eight-spaced fixture, maximum actual ACK due-to-service wait
is 29 ticks with both native guards, 14 with only the forward guard, 29 with
only the feedback guard, and 1 with neither. This illustrates that the
feedback-ready veto can dominate finite waiting time. The exact values are
source/plan-bound observations, **not a global bound**. Full original native
projection is promised only under both guards; a relaxed derived schedule
may preserve terminal payload while changing source-native timing/resource
traces.

The tail-off intervention left 266 delivered controls without an ACK across
27 native contexts, and produced **no absence certificates**. Service
completeness therefore depends on the explicitly enabled finite tail and
its budgets; merely selecting ACK priority is not a completion guarantee.

## Run on `fwork`

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v3efg_Cumulative_Native_Veto_Attribution_Milestone.tar.gz

bash search/spk_bv_v3efg_native_veto_attribution_cumulative_gate.sh \
  /tmp/spk-bv-v3bcd-episode-wait-prefix.json \
  /tmp/spk-bv-v3efg-native-veto-attribution.json

bash search/spk_bv_v3efg_inherited_regression_gate.sh
```

The report output is create-only and rejects existing/unsafe paths. Use a
new output filename for a rerun; never overwrite predecessor or frozen files.

## Scientific boundary and next step

This proves finite, source-backed **trace accounting** and guard sensitivity;
it does not prove global ACK deadlines, queue starvation-freedom, live-native
actor priority adoption, native learning, or hardware characteristics. The
next useful gate would require a new explicit native service opportunity or
bounded-veto assumption with independent evidence. No such contract is
promoted here.

S1=100%, S2=100%, S3=60%, S4=0%, S5=0%; total=52% (equal-weight stage
mean, unchanged). These are conservative roadmap estimates, not percentages
derived from the number of tests or stages named v3e–v3g.
