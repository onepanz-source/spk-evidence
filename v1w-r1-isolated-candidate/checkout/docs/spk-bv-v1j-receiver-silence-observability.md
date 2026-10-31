# SPK BV v1j - Receiver silence observability and missingness contract

**Status:** research-only / source-bound epistemic boundary. Not an SPK Architecture amendment, not an algebra rule, not a learned update.

## Scientific question

BV v1h and v1i established that the isolated, pre-episode substitution of A's `CMP(1)` by `CMP(2)` suppresses both A→B and B→C forward occurrences in the bounded original three-neuron fabric, and produces zero native feedback assessments and reverse deliveries. This is a *network outcome* observable to an experimenter comparing two independently run branches. It is **not information available to an event-only neuron B or C when no event arrives**.

The native original route/occurrence testimony v1g.1 is: A/PE0 channel 7 → B/PE1 channel 0; B/PE1 channel 7 → C/PE2 channel 0. Each original route is traversed twice. The original reverse assessment a1/a2 traverses C→B→A along the corresponding causal branches. C has no direct A→C forward edge. The original 2 assessments / 4 reverse deliveries are evidence-lineage traffic, not numerical judgments about the quality of A's choice.

## Bounded observability claim

Let \(H_R\) denote the *incoming event projection* of a recipient \(R\), without a separately attested expectation, synchronization obligation or observation-coverage witness. If \(H_R=\varnothing\), the observation can be compatible with distinct hidden causes: no emission at the sender, no expected causal input, upstream silence, an unspecified interruption, or other unobserved causes. For the experimentally observed branch, we know that A computed and suppressed emission **from the experimenter's full native replay**, not from B's or C's empty incoming event stream. The two illustrative worlds in the report are a logical ambiguity witness, **not two additionally replayed SPK networks**.

Therefore the event-only projection alone cannot certify any judgment sign for an absent spike. A claim about *expected-but-missing* traffic needs at least:

1. An expectation bound to a particular upstream decision **before** the episode, with authenticated source identity.
2. A predeclared observation deadline and demonstrably complete observation coverage for the interval (including evidence of non-events), not just a local timeout.
3. A predeclared receiver evaluation criterion, distinct from the fact of non-arrival.
4. An authenticated causal binding from the expected event to the sender's decision and a way to distinguish unobserved causes when necessary.

The current frozen reference contains none of those absence-witness certificates; adding a `deadline` or `coverage_declared=true` to a shadow plan remains only a declaration. The `classify_silence` function makes this explicit with its `MISSED_DECLARED_EXPECTATION_NOT_SOURCE_ATTESTED` result. It never emits a native judgment.

## Audit and fail-closed invariants

* Native v1i must be **reconstructed again** by its existing CLI (which itself independently reexecutes v1h) and compared byte for byte to the reference. The source-bound v1i/v1h/v1g.1/v1d SHA-256 chain must match.
* The original two native routes, four uniquely identified occurrences, their proper two causal parent pairings, and two distinct assessment IDs each moving C→B and B→A must agree. Each reverse relay must bind to the same original causal ancestor and occur later than the previous relay.
* The network intervention must preserve the original nodes and fabric, with variant counts A→B=0, B→C=0, assessments=0 and deliveries=0.
* Reports forbid inferred utility, independent causal votes, source-attested absence certificates, operator commits and learning claims.
* CLI inputs may not alias, be symlinks, reside inside the repository, or be oversized. Outputs are new files outside the repository only. Source files are checked again before publication.

## Replay on fwork

Extract this incremental archive in the existing `~/workspace/spk-backvalidation-v0` checkout. No frozen files are overwritten.

```bash
bash search/spk_bv_v1j_research_gate.sh

python -m search.spk_bv_v1j_silence_observability \
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
  --out /tmp/spk-bv-v1j-receiver-silence-observability.json
```

The native command may only be certified on a checkout containing the frozen Architecture v1 and historical research modules. Offline tests and document-only replay are not a substitute for that command.

## Next research gate

Define *who* can witness an expected but missing upstream event, through which independently authenticated observation protocol, and with what non-event coverage proof. Then define the recipient's actual criterion. Avoid treating the simulator's ability to see the full counterfactual as an ability of a recipient neuron itself.
