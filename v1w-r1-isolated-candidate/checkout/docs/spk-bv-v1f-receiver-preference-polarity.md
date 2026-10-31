# SPK BV v1f: conditional receiver preference polarity boundary

## Scientific question

BV v1e shows four changed native readouts among six *conditional* A-to-(B,C)
experiments, with declared experimental mapping `(sender emission 7) ->
(receiver ingress 0)`. The A-to-B and A-to-C routes have **not** been
attested by the frozen network, and B/C have not generated value judgments.

Can the same pair of downstream responses unambiguously determine whether A's
operand change is beneficial? **No.** Value depends on an independently specified
criterion. v1f illustrates this *non-identifiability* without fabricating votes.

## Predeclared contrast

The measured variable is the **count of outgoing channel-7 emissions** of B/C
in their local `_compute_local` result, restricted in this fixture to 0 or 1.
Two external policies are evaluated on the exact same v1e report:

- `maximize_receiver_emission_count`: preference sign +1 if variant emits more,
  -1 if less, 0 if tied.
- `minimize_receiver_emission_count`: exact opposite sign on differences.

These policies are deliberately opposite, synthetic, experimenter-defined and
not asserted to reflect neuron or task utility. The sign means only *which
branch is preferred under that criterion*, not reward, fitness, learning or
neuron-to-neuron judgment.

Predicted from the uploaded v1e matrix (subject to fwork source replay):

| Declared policy | +1 | -1 | 0 |
|---|---:|---:|---:|
| Maximize receiver emissions | 0 | 4 | 2 |
| Minimize receiver emissions | 4 | 0 | 2 |

B and C share the *declared* A-origin for each domain index, so six conditional
observations are **not** six independent causes. The output has three declared
shared-origin groups, zero certified independent votes and zero endogenous
receiver judgments. The two policies produce opposite preferences on exactly
four differences; no utility truth can be inferred.

## Native chain and reproducibility

The CLI takes v1e, v1d, v1c, v1b1, v1a and v0w reports. It applies the same
source-bound reconstruction used in v1e, invoking the existing frozen A1
`_compute_local`, regenerates v1d, regenerates **all of v1e**, then requires
exact dict equality with the supplied v1e. It records SHA-256 of v1e and all
upstream reference identities and checks the frozen code inventory before and
after. It refuses aliases, in-repository sources, symlink inputs, unsafe or
existing outputs. An independent research gate runs v1f tests followed by the
whole v1e inherited gate and Architecture v1 custody.

```
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v1f_Receiver_Preference_Polarity.tar.gz
bash search/spk_bv_v1f_research_gate.sh
python -m search.spk_bv_v1f_receiver_preference \
  --v1e /tmp/spk-bv-v1e-conditional-receiver-impact.json \
  --v1d /tmp/spk-bv-v1d-native-declared-criterion-13.json \
  --v1c /tmp/spk-bv-v1c-native-sensitivity.json \
  --v1b1 /tmp/spk-bv-v1b1-native-operator-replay.json \
  --v1a /tmp/spk-bv-v1a-symbolic-holdout.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --out /tmp/spk-bv-v1f-receiver-preference-polarity.json
```

## Claim boundaries

The result is a **polarity non-identifiability demonstration** using real
readouts of isolated native computations. It is not a network-scheduler trace
for the variant, not an observation of feedback from B/C, not credit assignment,
not an independent objective or proof of an admissible algebra rewrite. Frozen
neuron programs are never modified or updated. Further work must separately
establish native A-to-recipient route/event lineage, an endogenous recipient
assessment rule, a temporally available feedback packet, a bounded local
update, and prospective measured benefit under an external task criterion.
