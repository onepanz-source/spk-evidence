# SPK/* Back Validation v1n: Receiver Knowledge & Disclosure Lower Bound

## Exact scientific question

Given the native source-bound v1m evidence for the frozen A→B→C fabric,
what can **B** distinguish if its available view is limited to input events?
What *additional information* would a receiver-local experiment have to reveal
before B could distinguish source-port silence from transport loss, an
undelivered event from one that was never expected, and a covered absence from
an observation gap?

**Scope:** this is a finite **epistemic indistinguishability experiment**.
It is not a native authenticated watch channel. It is not an exhaustive proof
that the enumerated fields are sufficient in an arbitrary asynchronous network.
A simulated knowledge disclosure does not certify native message delivery.

## Native grounding (actual v1m)

- v1m completed four frozen scheduler arms (`original`/`variant` × `OFF`/`ON`).
- The sole direct path from A is `A→B:7→0`; C is downstream via `B→C:7→0`.
- In the **original** trace A emits twice and B consumes two occurrences.
- In the **isolated CMP(2) variant** A emits zero and B consumes zero.
- In both branches the v1m evidence comes from post-hoc producer-owned
  scheduler traces. There is no receiver-readable source-port attestation,
  precommit, guaranteed deadline, independently certified interval coverage,
  or independent two-port observer.
- No native missing-event witness, scored judgment, operator update or learning.

The CLI demands byte-exact reproduction of the entire v1m report from its
predecessor chain before producing the v1n output. The only mutable output is
an exclusive new JSON report; no SPK runtime or frozen module is patched.

## Finite worlds and knowledge tiers

The model includes **two source-bound, native POSTHOC count-worlds** (original
and variant), plus **six explicitly hypothetical worlds** including transport
loss, previously declared expectation, absence of expectation, lost monitor
coverage and two different internal causes. The hypothetical transport-loss
world is **not** a second frozen native scheduler replay. Its emission count
is simply a bounded model input.

| Information tier | Receiver-visible *in the shadow model* | Distinctions possible in this finite model |
|---|---|---|
| `T0_INGRESS_ONLY` | Number of received spikes | Cannot separate silent A from an emission lost on the link |
| `T1_PLUS_SENDER_PORT_DISCLOSURE` | T0 + apparent sender emission count | Can separate 0→0 from 2→0 as a formal information distinction |
| `T2_PLUS_PREDECISION_EXPECTATION` | T1 + declared expectedness before decision | Can distinguish a previously expected event from no expectation |
| `T3_PLUS_INDEPENDENT_INTERVAL_COVERAGE` | T2 + hypothetical independent coverage | Can separate a covered window from an observation gap |

**None of tiers T1–T3 is actually present as an authenticated native channel.**
At T1, even a disclosed positive/zero emission count only has evidentiary value
if its publisher and coverage are authenticated; the modeled distinction
alone is NOT a trusted missing-event certificate. T2/T3 are also *declared
hypothetical* fields, not implemented native records. Even the maximal T3
view leaves the **internal decision cause** ambiguous: two worlds share all
four observable fields but posit different causes.

The report exposes eight worlds, each world’s origin, four equivalence
partitions and five explicitly challenged pairs. It marks no shadow world
as a receiver judgment. One comparison anchors the receiver-ingress view of
the actual native variant to a *hypothetical* transport-loss world. This is a
logical counterexample to cause-identification from ingress alone, not a
claim that the native run actually suffered a transport loss.

## Limits, obligations, and next design work

1. Before promoting any absence evidence, define who issues a predecision
   expectation, who can acknowledge it, and which source authenticates it.
2. Specify an independent, bounded **coverage authority** for both endpoint
   windows. A producer-owned scheduler trace cannot impersonate that authority.
3. Give B a real receiver-readable path for this evidence. Its existence is
   currently absent, not merely untested.
4. Specify a **decision provenance record** independent of the monitored
   spike if one wants to attribute silence to a particular operator decision.
5. Only after these bounds may a separate local criterion and a causal
   credit mechanism be designed. Neither is implemented in v1n.

There is deliberately **no modification** to Core/Network v0, Compiler v0,
Architecture v1, or existing BV research modules.

## Installation and source-bound fwork experiment

```bash
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v1n_Receiver_Knowledge_Disclosure.tar.gz
bash search/spk_bv_v1n_research_gate.sh
python -m search.spk_bv_v1n_knowledge_disclosure \
  --v1m /tmp/spk-bv-v1m-native-passive-trace-projection.json \
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
  --out /tmp/spk-bv-v1n-receiver-knowledge-disclosure.json
```

For local, *non-native* source audit, `analyze(...)` may be applied to the
provided v1m/v1l/v1h/v1g1/v1d reports. That mode explicitly reports
`native_v1m_recomputation_verified_in_this_run=false`. Do not equate it with
the fwork CLI result, where the corresponding flag is true only after
byte-identical predecessor replay and four new native scheduler arms.
