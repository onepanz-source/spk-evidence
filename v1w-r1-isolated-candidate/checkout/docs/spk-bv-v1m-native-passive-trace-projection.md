# BV v1m · Post-hoc source-bound native endpoint projections

## Question
Can *frozen native scheduler records* separately show A's emission on channel 7,
B's ingress on channel 0, B's emission on channel 7 and C's ingress on channel 0,
for the original and the isolated CMP(1)->CMP(2) intervention?

## Observation and authority
This read-only instrument collects the **native simulator's own** batch, emission,
forward occurrence, link-grant and terminal records from **four complete replay
arms** (original/variant × OFF/ON). It does not change any SPK frozen module.
Prior to collection the entire v1l report is reproduced **byte-for-byte**,
including its native v1k/j/i/h predecessor chain. During collection the frozen
fixture and sources are pinned, and the intervention is applied only to a copy.
Each arm is reconciled against **v1h whole result SHA**, v1h exact forward audit
and v1g.1's original occurrence IDs, timestamps and ancestry.

**Crucial limit:** an emission record and an ingress record extracted from the
same scheduler run are not independent two-port witnesses and **were not seen
by the receiver neuron**. Zero observed emissions within a completed bounded
simulator run are not an independently certified absent event at the receiver.
There is no signed commitment, guaranteed deadline/coverage, observer-to-B
channel, endogenous criterion or neuron-local commit/learning mechanism.

The only native topology is A→B→C. C can observe a B→C ingress, not a direct
A→C link. No event in one intervention branch is assigned the identifier of a
missing event in the other intervention branch.

## Safety assertions
- Each forward emission routed on a static link joins the exact number of
  delivered/consumed occurrences; times and link grants are audited by v1g.1.
- Zero-occurrence variants cannot conceal emitted spikes, grants or consumers;
  terminal counts reconcile via the v1h forward auditor.
- Four native arms exactly match v1h complete forward summaries and whole
  scheduler-result hashes, not merely integer counters.
- Changed frozen source, fixture, route, predecessor JSON, or altered report
  bytes causes fail-closed rejection.
- No inference of internal sender decision, independent causal votes,
  missing-event approval, utility or native learning.

## Commands

```bash
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v1m_Native_Passive_Trace_Projection.tar.gz
bash search/spk_bv_v1m_research_gate.sh
python -m search.spk_bv_v1m_native_passive_projection \
  --v1l /tmp/spk-bv-v1l-two-port-observer.json \
  --v1k /tmp/spk-bv-v1k-receiver-witness-authority.json \
  --v1j /tmp/spk-bv-v1j-receiver-silence-observability.json \
  --v1i /tmp/spk-bv-v1i-native-feedback-silence.json \
  --v1h /tmp/spk-bv-v1h-isolated-network-counterfactual.json \
  --v1g1 /tmp/spk-bv-v1g1-native-original-route-lineage.json \
  --v1f /tmp/spk-bv-v1f-receiver-preference-polarity.json \
  --v1e /tmp/spk-bv-v1e-conditional-receiver-impact.json \
  --v1d /tmp/spk-bv-v1d-native-declared-criterion-13.json \
  --v1c /tmp/spk-bv-v1c-native-sensitivity.json \
  --v1b1 /tmp/spk-bv-v1b1-native-operator-replay.json \
  --v1a /tmp/spk-bv-v1a-symbolic-holdout.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --out /tmp/spk-bv-v1m-native-passive-trace-projection.json
```

v1m intentionally requires the v1l predecessor with `--demo-lab` and verifies
exact replay of its built-in ten laboratory scenarios. Output creation is
exclusive and rejects repository paths, input aliases and symlink inputs.
