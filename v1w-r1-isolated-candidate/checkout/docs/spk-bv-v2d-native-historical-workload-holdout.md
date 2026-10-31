# SPK BV v2d: Historical native workload holdout vs explicit-input micro-runtime

**Status:** `PRIOR_NATIVE_COINCIDENT_INPUT_COUNTEREXAMPLE_TO_MICRO_RELAY_COUNTS`.
Research-only comparison; no frozen source modifications, no new native scheduler runs.

## Purpose and independence

v2c fitted the bounded research executor's time policy (first tick 1, input gap
2, hop delay 1) to *existing* native posthoc emission timestamps for the
original two-event fixture. A fit on the same fixture does not establish
scheduler or instruction equivalence.

v2d uses the **pre-existing v0w native workload-sensitivity report**, whose
five exogenous workload classes were produced by the original frozen scheduler
prior to v2c. Native counts are drawn **only** from that saved v0w artifact;
no semantic observations are invented from missing native event records.
A new standalone micro-executor supports an *explicit tuple* of external input
ticks. Consequently, coincident inputs `(1, 1)` and irregular repeated inputs
`(1, 3, 9, 11)` can be compared on equal declared exogenous timestamps, unlike
v2c's fixed-gap input policy.

The v2d micro `relay` is a new research rule. It **does not implement**
`('CMP',1)`; the micro `BV on` flag is a label only. The v0w native fixture uses
its frozen SPK program, transport, feedback policy and three native capacity
profiles. The micro executor does not reproduce those resource/feedback rules.

## Pre-registered finite comparison boundaries

Compare each of five v0w workload classes across three source-attested native
capacity profiles and forward-first BV OFF/ON: **30 historical native-to-micro
aggregate projection cells**. Native profiles `(fabric slots, max inflight)`:
`(1,4), (2,1), (2,4)`; no native full event trace is available for these
holdouts. New micro runs: 10 workloads/modes × two observer settings = **20**.

| v0w native workload | Native input ticks | Native emissions / terminal | Micro emissions / terminal | Native-to-micro aggregate equality |
|---|---|---:|---:|---|
| baseline | [1,3] | 6 / 2 | 6 / 2 | 6 of 6 comparisons |
| coincident | [1,1] | 3 / 1 | 6 / 2 | **0 of 6** |
| second_plus_1 | [1,4] | 6 / 2 | 6 / 2 | 6 of 6 |
| second_plus_3 | [1,6] | 6 / 2 | 6 / 2 | 6 of 6 |
| repeated_episode | [1,3,9,11] | 12 / 4 | 12 / 4 | 6 of 6 |

These comparisons demonstrate a finite **counterexample to aggregate count
parity** in the coincident workload, *not* the reason for the difference. The
native trace may group or compute coincident events in ways that differ from
the micro admissions, but v0w's aggregate counters do not prove which mechanism
caused the contrast. v2d therefore does not claim native coalescing or
independent observation of native ingress events.

Micro events are produced during micro execution, and the micro output is equal
with observer OFF/ON, subject to bounded fixture/scheduling limitations. Observer
records are neither independently authenticated nor receiver-local evidence.

## Inputs, integrity and native custody

- Attested v2c report, and predecessors v2b, v2a, v1q, v1m, v1z, v1y, v1x.
- Earlier native v0w report, produced by the frozen native workload experiment.
- All predecessor reports must be sourced from the same experiment lineage.
- v0w uses its **original compact JSON serialization**, not later pretty-printed
  canonical v1r-v2c JSON. CLI requires byte-for-byte reserialization under each
  artifact's own format; it refuses unexpected reformatting and symlink/alias
  inputs.
- v2c is fully recomputed, byte-for-byte, from predecessors; original native
  fixture SHA in v0w must match v1q; baseline native result SHA in v0w must match
  v1x, and frozen source pins must agree with the known v0w producer sources.
- Default fwork CLI rechecks frozen source bytes before/after the experiment.
  `--contract-only` skips new frozen-source custody and **must not** be called
  native-attested. Neither mode executes the frozen scheduler anew.
- The new micro executor's source SHA is pinned in v2d CLI. No frozen file or
  previous versioned micro executor is modified.

## Installation and short gate

```bash
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v2d_Historical_Native_Workload_Holdout.tar.gz
bash search/spk_bv_v2d_research_gate.sh
```

## Full source-bound report on fwork

```bash
python -m search.spk_bv_v2d_native_holdout_differential \
  --v2c /tmp/spk-bv-v2c-time-order-differential.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --v2b /tmp/spk-bv-v2b-native-micro-differential.json \
  --v2a /tmp/spk-bv-v2a-bounded-executor.json \
  --v1q /tmp/spk-bv-v1q-native-factorial-interactions.json \
  --v1m /tmp/spk-bv-v1m-native-passive-trace-projection.json \
  --v1z /tmp/spk-bv-v1z-native-observer-admission.json \
  --v1y /tmp/spk-bv-v1y-native-external-probe.json \
  --v1x /tmp/spk-bv-v1x-reference-observation-port.json \
  --out /tmp/spk-bv-v2d-native-historical-holdout.json
```

Substitute the actual existing v0w report path if its local filename is
different. `--out` must be a previously nonexistent path. No overwrite and no
move/delete of validated predecessor evidence is needed.

## Limits and next release

- This is **historical native source-bound comparison**, not 30 fresh native
  scheduler executions. The report explicitly records zero new native runs.
- Aggregate coincidences on 24 cells do not establish state, route, timing,
  CMP or BV equivalence. The 6 coincident differences falsify count equivalence
  of the particular micro-relay model at equal input timestamps.
- v0w saved no native A/B per-event holdout emission trace; no native time
  alignment claims are made on the holdout cells.
- A future executor must specify native **batch admission** and `CMP` operator
  behavior on simultaneous inputs and then test on unfit fixtures. Do not
  retrofit `relay` to the six observations and call that independent validation.
- Zero independent absence certificates, native control delivery to B,
  local value judgments, causal learning credits, operator updates or learning.

The 5-stage overall Back Validation checkpoint remains 100%, 100%, 95%, 60%,
0%, mean 71% (unchanged); this research delta is not proof of native integration.
