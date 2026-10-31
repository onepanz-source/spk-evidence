# SPK V5-T3d Physical-successor public UCI onset falsification

Research-only additive milestone. Does not alter frozen Core, Network, Compiler, Architecture v1, A1b, or BV v0e. T3a/T3b/T3c untouched.

## Precisely different task and physical-time assumptions

T3a/T3c adapted **one simultaneous sensor record** into two synthetic neural ticks. That protocol was exactly a *same-record* Light>=200 AND CO2>=600 threshold, not physical temporal learning. T3d instead processes **consecutive real source records**, with a checked 59/60/61-second timestamp interval. Earlier row's `Light<200` emits `C0` at A tick 10; earlier `Light>=200` emits `C1` at tick 10; later row's `Light>=200` emits `P` at tick 11. Low later light emits no P. A's frozen `TEMPORAL` then detects **low-to-high light crossing across distinct measurements**. This is a real ordering feature, although the explicit one-tick-per-record mapping is an *experimental time discretization*, not measured A1b wall-clock physical execution.

Target for the independent auditor: **photograph-label occupancy onset** defined by `previous.Occupancy==0 and current.Occupancy==1`. No photographic label, data row ID, or future measurement is provided as input to A; the auditor reads labels after the A1b forward execution returns. This onset task is researcher-defined after seeing public labels, not an independent blind challenge, a native C reward, or learned behavior. All candidate A1b programs were already frozen. T3d performs **NO fit/reward-based selection**.

## What this proves and does not prove

Source-actual A1b computation is sensitive to predecessor order. Pairs having the same bright current sensor but different predecessor context give different TEMPORAL outputs. All 20,557 source-successor pairs reproduce a two-reading rising-edge predicate, `Light_previous<200 AND Light_current>=200`. This is NOT evidence of superiority over the same trivial two-reading classical rule. The previously recorded UCI result T3c **does not carry forward** as a performance claim on the new onset task.

Native A1b executed individually on every pair for the existing `temporal`, `overemit`, `silent` programs. The program `overemit` becomes a current-brightness detector; `silent` remains negative; `temporal` becomes a rising-edge detector. No program updates, no RL, no native reverse channel, no independent blinded holdout.

### Original UCI chronological partitions (posthoc diagnostic, full data)

| Partition | Physical successor pairs | Occupancy onsets | Detected onsets via TEMPORAL | TEMPORAL FP | TEMPORAL FN | TEMPORAL errors | SILENT errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train (Feb 4–10) | 8142 | 20 | 5 | 20 | 15 | 35 | 20 |
| early (Feb 2–4, before train) | 2664 | 13 | 2 | 1 | 11 | 12 | 13 |
| late (Feb 11–18, public) | 9751 | 24 | 4 | 21 | 20 | 41 | 24 |

Extremely rare occupancy onsets make always-silent competitive or preferable by raw error count; balanced accuracy differs and is recorded separately. Consecutive one-minute pairs share observations, so row-level confidence intervals or independence claims would be wrong. All thresholds and task are *posthoc experimental choices*: no prospective validation, no statistical guarantee.

## Run on Fedora fwork, original immutable files

First run gate (can omit two args for source/test-only; with args validates full external report):

```bash
bash search/spk_v5_t3d_real_transition_gate.sh \
  ~/Scaricati/occupancy \
  /tmp/spk-v5-t3c-original-uci-full-coverage.json
```

Or create report explicitly using the original files and the **exact** earlier T3c report:

```bash
python search/spk_v5_t3d_real_transition.py \
  --train ~/Scaricati/occupancy/datatraining.txt \
  --early ~/Scaricati/occupancy/datatest.txt \
  --late ~/Scaricati/occupancy/datatest2.txt \
  --t3c-report /tmp/spk-v5-t3c-original-uci-full-coverage.json \
  --t3c-sha256 388147a99e6407157b3ca3f4650d11b2cb169d25d292bbc25bcd1296ff7b0d01 \
  --out /tmp/spk-v5-t3d-real-successor.json
```

All reports are create-only outside repo; original UCI files must retain their raw-byte SHA256; an exact prior T3c canonical report must be supplied. The bundled reference JSON pins the expected empirical report but does not bundle third-party input files.

## Gate interpretation

- Verified: external physical successor timestamps and A1b temporal ordering; full replay; causal sensor/label isolation; SHA custody; static-two-reading equivalence; posthoc error metrics and absence of false learning claims.
- NOT verified: real hardware tick duration, on-policy endogenous rewards, native credit for silence, native learner, blind holdout, independent sensor authority, statistical performance lift.
- **Research verdict**: temporal input capability PASS, usefulness for occupancy-onset detection **NOT ESTABLISHED**; on later public data it loses by total errors to SILENT; T3 blind and native learning remain blocked.
