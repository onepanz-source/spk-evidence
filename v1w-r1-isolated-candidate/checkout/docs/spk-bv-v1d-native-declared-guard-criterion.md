# SPK BV v1d: preregistered synthetic guard objective on native A1 local kernel

## Scientific question

Can **one of the native operand perturbations already attested by v1c** improve a
**fixed, explicitly synthetic** criterion on the A1 native `_compute_local` boolean
`guard` readout, in a disjoint future-like evaluation subset that is **not used
for candidate selection**?

The criterion is declared in immutable source, **before kernel calls**:
`guard == (number_of_input_channels_equal_to_0 >= 2)`. The target is generated
from the input, NOT from independent environmental ground truth, feedback,
actual receiver judgments or an oracle. This objective is deliberately artificial.

## Custody and design

* Full reconstruction of v1b.1 OFF baseline (6 batches), then v1c (5x6=30
  comparisons) must exactly equal both uploaded attestations.
* Frozen A1 `_compute_local`, neuron case, original dataclass nodes and their
  instruction programs never modified. Only ephemeral `replace` copies used.
* Source and JSON file SHA-256 checked. Existing output refused.
* TRAIN indices [0,1,2] at (timestamp=10, previous_tick=9) choose one of five
  candidate *operand* perturbations by maximal correctness gain, fixed source
  order as tie-breaker; evaluation is not read before selection.
* EVALUATION indices [3,4,5] at (timestamp=11, previous_tick=10) calculate a
  paired score only for the already selected candidate, with no native commit.
* Local kernel args are freshly allocated and checked for mutation; two calls
  must yield identical, strictly typed results. Only boolean `guard` is scored,
  not output channel identity, network behavior, power, latency, or hardware.
* Training and evaluation are disjoint by tuple *index*, though they may share
  identical input values (e.g. raw 0/channels(0,) versus raw 1/channels(0,)).
  Different previous_tick/timestamp is NOT statistical heldout independence.

## Rejected claims

A positive evaluation score is **only** improvement against an openly declared
synthetic guard criterion in a six-case bounded local experiment. It is **not**:
(a) evidence of native Back Validation information value, (b) validated truth
of a receiver judgment, (c) a causal credit assignment, (d) a learned policy,
(e) admissible algebraic rewriting, or (f) a network-level improvement.
Zero native judgments and zero updates are mandatory.

## Commands

```bash
bash search/spk_bv_v1d_research_gate.sh
python -m search.spk_bv_v1d_native_criterion \
  --v1c /tmp/spk-bv-v1c-native-sensitivity.json \
  --v1b1 /tmp/spk-bv-v1b1-native-operator-replay.json \
  --v1a /tmp/spk-bv-v1a-symbolic-holdout.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --out /tmp/spk-bv-v1d-native-declared-criterion-13.json
```
