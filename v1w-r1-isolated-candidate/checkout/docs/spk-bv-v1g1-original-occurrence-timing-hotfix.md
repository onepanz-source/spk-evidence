# SPK BV v1g.1: Original occurrence timing versus link-grant timing

Research-only hotfix; no changes to frozen Architecture v1, Network, Core or Compiler.
The v1g CLI on fwork rejected a native row as `invalid occurrence timing/parent fields`.
The original v1g contract required `delivered_at >= emitted_at + delay` without
consulting `forward.link_grants`. That conflated a route's nominal `delay`
with the native transport admission/grant chronology.

## Corrected interpretation

1. Every occurrence retains a unique static source→target route and the route's
   nominal delay; the route and occurrence delay **must** match exactly.
2. `emitted_at` and `delivered_at` are integers with `0 <= emitted_at <= delivered_at`.
3. When native `forward.link_grants` are present, each occurrence must have **one
   and only one** corresponding grant matched by native `id`, source/target,
   source/target PE and exact `delivered_at`. A grant must have valid ordered
   `emitted_at <= grant.tick <= grant.delivered_at`.
4. The route's numeric `delay` is **not independently added** to `emitted_at`
   to reject a transport record already corroborated by its corresponding
   native grant. This is an observation rule, **not** a hardware latency claim.
5. When `link_grants` are absent, synthetic contract tests must still meet
   the original conservative `delivered_at >= emitted_at + delay` check. No
   exceptional timing can pass without a corroborating native grant.
6. Native occurrence `parents` may be list or tuple; each entry still must be a
   distinct, non-self string. Recorded output normalizes them to a list.
7. All previous route multiplicity, ancestor ordering, batch consumption,
   OFF/ON preservation and reverse-packet evidence checks remain in force.

An added report field `original_forward_transport_grants_joined` discloses
whether both OFF and ON had per-occurrence transport evidence. The hotfix
preserves the original v1g report schema and status; it does not attest
operator substitutions or learning.

## On fwork

```
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v1g1_Original_Occurrence_Timing_Hotfix.tar.gz
bash search/spk_bv_v1g1_research_gate.sh

python -m search.spk_bv_v1g_native_route_lineage \
  --v1f /tmp/spk-bv-v1f-receiver-preference-polarity.json \
  --v1e /tmp/spk-bv-v1e-conditional-receiver-impact.json \
  --v1d /tmp/spk-bv-v1d-native-declared-criterion-13.json \
  --v1c /tmp/spk-bv-v1c-native-sensitivity.json \
  --v1b1 /tmp/spk-bv-v1b1-native-operator-replay.json \
  --v1a /tmp/spk-bv-v1a-symbolic-holdout.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --out /tmp/spk-bv-v1g1-native-original-route-lineage.json
```

Output uses exclusive create, does not overwrite existing files.

## Validation scope

The local regression suite can validate synthetic timing/grant cases, not
observe fwork's frozen native producer. The native CLI is a separate gate.
If that gate still rejects the real fixture, the improved diagnostic reports
an occurrence's index, temporal scalar values and parent collection type,
without suppressing the evidence failure. Do not certify native topology until
it passes.
