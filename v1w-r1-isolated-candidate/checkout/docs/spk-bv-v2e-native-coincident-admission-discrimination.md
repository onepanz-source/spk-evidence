# SPK BV v2e · Frozen-native coincident admission discrimination

**Scope.** Additive **research-owned** tool. The frozen live scheduler, producer,
Core, Network, Compiler and Architecture are never edited. `v2d` was already a
source-bound contrast, not a proof of *why* coincident inputs produce 3 native
emissions instead of 6 micro emissions. v2e probes that uncertainty directly.

## Pre-registered experiment

`15` named workloads use only both native input event templates, their tuple
order, and external integer timestamps. No new CMP, node program, fabric,
transport, link capacity or event channel is fabricated. Run each workload with:
BV OFF/forward-first, BV ON/forward-first, BV ON/feedback-first, always against
**the same exact cell input**. This yields **45 new frozen-native executions**.

| Workload | External event-template index at tick |
|---|---|
| single_first | 0@1 |
| single_second | 1@1 |
| original_gap2 | 0@1, 1@3 |
| mixed_coincident | 0@1, 1@1 |
| reverse_coincident | 1@1, 0@1 |
| first_first_coincident | 0@1, 0@1 |
| second_second_coincident | 1@1, 1@1 |
| adjacent | 0@1, 1@2 |
| delayed | 0@1, 1@4 |
| triple_mixed_coincident | 0@1, 1@1, 0@1 |
| triple_first_coincident | 0@1, 0@1, 0@1 |
| triple_staggered | 0@1, 1@2, 0@3 |
| two_coincident_clusters | 0@1, 1@1, 0@3, 1@3 |
| triple_gap | 0@1, 1@3, 0@5 |
| repeated_episode | 0@1, 1@3, 0@9, 1@11 |

The four historical configurations `original_gap2`, `mixed_coincident`,
`delayed` and `repeated_episode` MUST match preexisting v0w **whole-result
SHA-256**, metrics, forward states and payload hashes, for all three BV
controls. This yields **12 independently anchored output comparisons**.
No field is silently skipped on anchor mismatch.

## Hypotheses, not inferred laws

Three simple count predictors are recorded for every workload: 3 emissions per
external event; 3 per distinct input timestamp; 3 per distinct native input
template and timestamp. The final predictor is **unidentifiable** if the two
source templates coincide after normalizing their timestamps. An agreement or
falsification is a *finite scalar count observation* only. It does not show
which layer coalesces inputs: source admission, neuron `_compute_local`,
forward scheduler batching, quota, cross-PE link, or something else.

Native v0e result summaries expose `processed_events`, `processed_batches`,
`forward_batches`, `forward_emissions`, states and SHA-256 of the full result.
They are captured per control for later interpretation. No native semantic
online callback, independent clock, receiver delivery or absence witness is
created, and no operator update or learning is claimed.

## Run on fwork

```
cd ~/workspace/spk-backvalidation-v0
bash search/spk_bv_v2e_research_gate.sh
python -m search.spk_bv_v2e_native_admission_discrimination \
  --v2d /tmp/spk-bv-v2d-native-historical-holdout.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --out /tmp/spk-bv-v2e-native-admission-discrimination.json
```

The default requires frozen source hashes, real native fixture and imported
frozen source locations before executing. Each of the 45 native executions
retains the same fixture input as its OFF/ON comparators; no failed or
unavailable cell is dropped. The output uses exclusive creation and is never
stored in the source tree.

For an **offline contract only** (no native source verification or execution),
add `--contract-only` and use a different, nonexistent output filename.
Do **not** treat that report as native attestation.

## Promotion boundary

Even if one of the hypotheses explains all 15 counts, it does not establish
full CMP operator equivalence, operator state transitions, native event
identity, causal credit, native receiver knowledge, timing independence,
or learning. Additional fresh tests and direct source-level comparison would
be needed. The ten v1w native proof obligations remain open.
