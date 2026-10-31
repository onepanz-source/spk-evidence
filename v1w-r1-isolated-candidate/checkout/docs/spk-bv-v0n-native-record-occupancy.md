# SPK/* BV v0n: observed native grant/delivery occupancy (research, read-only)

## Inputs and provenance

Requires installed v0i, v0j, v0k, v0l and v0m modules. No frozen packages or native v0h source files changed. Reads the native pairing report generated in v0m; optionally requires the complete v0k fixture capture and v0l dossier to recompute and compare the source-bound pairing before issuing a source-verified observational report. **The report-only mode must not be called 'native verified'.**

The user-supplied v0m report from 2026-10-17 has `native_fixture_sha256=a580e8382ef18c04c479f4f969b2150efe4cb6a14f1f4d835e5a62c8015da8b0`, `joined_pair_multiset_sha256=c7ab10027a5f0aee8e7c4e1eb558785196a4f8ae52602100d8e62c2a5dc5c1c0`, 22 paired delivery/grant records, all local PE, 18 native independent-receiver flags and sum of reported `wait` 66. Those are **record facts**, not performance assertions.

## Mathematical observational accounting

Let `G_t` and `D_t` denote native `grants_by_tick` and `deliveries_by_tick` counts at tick `t` taken from the validated v0m report. `B_t = B_{t-1} + G_t - D_t` is the *end-of-tick unmatched-grant count*; `B_t >= 0` and final `B_t = 0` are required. This is logical evidence accounting; it is neither transport queue occupancy nor a physical hardware buffer measurement.

For any tick where both types of event occur, their internal sequence is unknown. Thus the conservative upper bound on *within-tick* pending grant records is `B_{t-1} + G_t`, not `B_t`. The tick area `sum((t[i]-t[i-1])*B_(t[i-1]))` is an integral over outstanding recorded grants. It is **not** the sum of native `wait`, not CPU cycles and not energy.

For the user-supplied 22-pair v0m report, the report-only calculation gives:

- `end_of_tick_undelivered_grants_peak = 2`.
- `within_tick_grant_first_peak_upper_bound = 4`.
- `bounded_grant_delivery_tick_area = 22` grant-tick observational units.
- `grant_and_delivery_coactive_tick_count = 10`.
- `native_reported_wait_sum = 66`, i.e. mean **reported native wait** = 3 per grant, not observed traversal or queueing latency.

The 22 grant records span ticks 9–19 (2 per tick) and 22 delivery records span ticks 10–20 (2 per tick). All 22 are local to one PE; these facts cannot be extrapolated to remote-PE network cost. The status of the report-only output remains `BOUND_V0M_REPORT_OBSERVATIONAL_ONLY`.

## Gate and production verification

```bash
cd ~/workspace/spk-backvalidation-v0
tar -tzf ~/Scaricati/spk-bv-v0n-native-occupancy-research.tar.gz
tar -xzf ~/Scaricati/spk-bv-v0n-native-occupancy-research.tar.gz
bash search/spk_bv_v0n_research_gate.sh

python -m search.spk_bv_v0n_observe \
  --pairing /tmp/spk-bv-v0m-native-pairing.json \
  --capture /tmp/spk-bv-v0k-native-fixture.json \
  --dossier /tmp/spk-bv-v0l-native-dossier.json \
  --out /tmp/spk-bv-v0n-native-verified.json \
  --expected-fixture-sha a580e8382ef18c04c479f4f969b2150efe4cb6a14f1f4d835e5a62c8015da8b0

bash search/spk_bv_credit_v0a_full_regression.sh
```

The `--capture` and `--dossier` arguments must be supplied **together**; omitting both produces only a report-bound, not source-recomputed, analysis. Output must not exist. No source writes or modifications to frozen Architecture v1 paths.

## What is and is not validated

A source-verified v0n output would establish correct *recomputation of the v0m record pairing* and grant/delivery aggregate accounting for this 22-packet pytest fixture. It would not establish stress-case 528 identities, native to v0i contextual mapping, deduplicated causal votes, forward throughput effects, counterfactual performance under equal workloads, cross-PE costs or compression/learning benefits.

Next acceptance step should be source-verified, paired feedback-enabled vs feedback-disabled **scheduler** runs under the same admitted workload, comparing forward completion time and memory/link grant demand. The 528-packet stress trace needs its own lossless native acquisition rather than assuming this 22-packet fixture represents it. Design these experiments in research only; do not change frozen components.
