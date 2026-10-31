# SPK/* Back Validation v4g–v4i — exact finite native opportunity coverage

**Status:** `EXACT_FINITE_COVERAGE_ONLY_NO_NATIVE_RESERVATION_OR_LIVENESS`

**Scope:** source-backed research only. This checkpoint does not modify the
frozen native `live_dual_scheduler_v0e.py`, Architecture v1, Core, Network or
Compiler. It does not install an ACK scheduler or train the neuron's P/S state.

## Why this phase exists

The prior v4d–v4f observation contains 1,359 overlapping four-tick windows in
which a source-ready ACK was not granted. Of these, 950 windows had **no
additional PE+O/E-memory slot** available anywhere within the window. Those
are overlapping constraints, not 950 independent jobs. An exact interval
covering calculation is necessary before interpreting service demand.

## Three source-bound steps

1. **v4g — finite opportunity model.** Replay all 18 signed frozen native
   executions. Align per-tick original PE and owner/O/E memory occupation
   with the 72 signed derived-source FIFO ACK contexts; isolate contiguous
   source-ready/no-real-grant runs. Real grants split these runs.
2. **v4h — exact offline frontier.** For each complete W-tick window within
   a run, demand one *hypothetical* coverage tick. A DP over distance to the
   last coverage event finds (a) minimum total covering ticks with a
   non-spare tie break, (b) minimum non-spare covering ticks with a count tie
   break, and (c) strict feasibility using **only** observed free native
   slots. Non-spare candidate ticks are an **optimistic relaxation**: no
   valid preemption, reserved PE, O/E memory or receiver credit is inferred.
3. **v4i — signed audit, exhaustive proof harness, closed boundary.** Compare
   exactly with the v4d–v4f window counts, reject changed signed reports or
   code, compare the DP to independent exhaustive subsets on all boolean
   free-slot patterns up to seven ticks, and preserve negative/no-admission
   assertions.

## Exact finite problem

For a source-ready/no-grant run of length `L`, with W in `{2,4,8}`, choose
candidate tick indices `S` such that every complete interval
`[i,i+W-1]`, `0 <= i <= L-W`, contains some index in `S`.

- Without capacity restrictions, the minimum number of covering ticks is
  `floor(L/W)` for `L >= W` (otherwise zero).
- A strict unchanged-native covering tick needs **simultaneous** unused
  global PE, owner PE, owner memory, O and E domain budget.
- Any complete W-window with *zero* strict native spare ticks proves
  unchanged-native spare-only coverage impossible for that context.
- The optimistic frontier admits non-spare tick candidates solely to bound
  contention. It does not prove that displacement can actually free every
  required resource, or preserve timing of original forward/BV operations.
- Each source context retains its own counterfactual; no simultaneous
  occurrence, independence or statistical probability is assumed.

| W ticks | Complete overlapping no-grant windows | Windows with no native spare | Infeasible strict contexts / 72 | Minimum hypothetical covering ticks (unrestricted) | Minimum optimistic non-spare covering ticks | All covering ticks at min non-spare |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 1,615 | 1,128 | 64 | 846 | 610 | 853 |
| 4 | 1,359 | 950 | 50 | 399 | 280 | 403 |
| 8 | 955 | 708 | 32 | 161 | 112 | 161 |

The unrestricted minimum covering count may be *lower* than the number
of ticks needed to minimize non-spare conflicts, because the objectives
are different. For example at W=4, 399 total coverage ticks may entail
284 non-spare selections, while 403 total can reduce that number to 280.

**Important limitation:** Candidate ACKs are never actually issued. If one
were issued, source-ready backlog and subsequent grant traces could change.
The finite source trace is therefore a bound on the original observation,
not a realizable live-service trace. Short runs with no complete W-window
make no claim; neither does this checkpoint certify continuations beyond
the observed native horizon or the v4a–v4c conditional FIFO rank deadline.

## Admission boundary

No choice of W or queue-rank Q is adopted. A future versioned arbiter must
define owner/global PE authority, O/E memory custody, consumer credit,
finite-horizon admissions, forward/BV preemption effects, and a genuine
native counterfactual schedule, then test deadlines and regressions. There
is no native ACK liveness theorem and no native P/S learning from this work.

## Reproducible gate on fwork

Extract the cumulative overlay inside an up-to-date `spk-backvalidation-v0`
checkout with `tar --keep-old-files` (preserves previously frozen files). Use
separate **existing** signed reports from v3tuv, v4abc and v4def. Specify a
new, nonexistent v4ghi output path:

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_BV_v4ghi_Exact_Native_Coverage_Frontier_Milestone.tar.gz
bash search/spk_bv_v4ghi_native_coverage_frontier_gate.sh \
  /tmp/spk-bv-v3tuv-grant-rank.json \
  /tmp/spk-bv-v4abc-native-contract-candidate.json \
  /tmp/spk-bv-v4def-native-capacity-envelope.json \
  /tmp/spk-bv-v4ghi-exact-native-coverage-frontier.json
bash search/spk_bv_v4ghi_inherited_regression_gate.sh
```

Source inputs and previous report have exact SHA-256 pins in the package.
The CLI is create-only and rejects overwrites, symlinks, unexpected source
changes, altered native replay outputs or altered signed predecessor bytes.
