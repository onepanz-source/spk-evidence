# SPK/* Back Validation · v1e conditional receiver impact (research only)

## Purpose and bounded question

After v1d, the selected operand change of the original frozen fixture is
A `CMP(1) -> CMP(2)`. On v1d's three subsequent *synthetic evaluation* cases
its declared guard objective changes from 1/3 to 3/3. Those labels are not
externally certified, and no receiver assessed any spike.

v1e asks one *different* question:

> If one predeclared, hypothetical entry translation maps A's emitted channel
> `7` onto the incoming channel `0` of the separately admitted frozen B or C
> kernel, does the local receiver readout differ under the two A emission
> alternatives?

v1e is an isolated kernel-level **conditional response probe**. It is not a
native network route replay, native assessment, learning experiment, nor
feedback credit measurement. Nothing in v1e proves B and C are both real
recipients of A's actual spike, or that any particular native fabric links
channel `7` to ingress `0` in the specified circumstances.

## Predeclared, intentionally unproven handoff

* Sender: A; emission domain: `()` or `(7,)`. Unknown emission patterns are
  rejected, not silently mapped.
* Distinct conditional receivers: B and C, each evaluated **independently**
  without carrying a reply downstream, changing topology or replaying the
  actual network scheduler.
* Declared translation only: `()` -> `()`; `(7,)` -> `(0,)`.
* The receiver starts each paired observation from its immutable `initial_raw`
  with `prior_tick=11`, `timestamp=12`. These are controlled test conditions,
  **not** reconstruction of an actual native receiver runtime history.
* Only v1d's three evaluation inputs, indices `(3,4,5)`, are examined;
  original/candidate A readouts are recomputed using `_compute_local` at
  `timestamp=11` and compared byte-for-byte with the entire stored v1d
  readouts.
* Each conditional B/C kernel result is independently executed twice,
  checking deterministic output, original-object immutability and input-argument
  immutability. Outputs are `raw`, `bool guard`, and emitted channels.
* The sole classifications are `SAME` and `DIFFERENT` at the receiver output.
  Guard/emission deltas are recorded but **not** scored as desirable.

## Integrity obligations

The CLI takes five external, read-only JSON references `v1d,v1c,v1b1,v1a,v0w`.
It declines existing output paths, repository-contained inputs/outputs,
symlinks, hard-link input aliases, oversized inputs and intra-run source or
reference changes. The CLI reproduces the complete v1b.1 native OFF replay,
then complete v1c native operand sensitivity, then v1d's criterion experiment
before generating the v1e conditional receiver probe. Frozen Architecture v1
source hashes are revalidated before/after. The complete stored v1d JSON must
match the fresh, genuine native recomputation.

The output explicitly declares `network_route_attested: false`,
`native_feedback_packet_attested: false`, `native_judgments_observed: 0`,
`native_updates_applied: 0`, `causal_credit_identified: false`, and
`native_learning_proven: false`.

The unit tests use synthetic doubles and do **not** attest a successful native
execution. Run the separate native CLI on `fwork` for real A1 kernel evidence.

## On fwork

Extract the incremental archive at the repository root; no frozen module is
modified.

```bash
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v1e_Conditional_Receiver_Impact.tar.gz
bash search/spk_bv_v1e_research_gate.sh
```

Run the native revalidation, with a **new, non-existing** output path:

```bash
python -m search.spk_bv_v1e_receiver_impact \
  --v1d /tmp/spk-bv-v1d-native-declared-criterion-13.json \
  --v1c /tmp/spk-bv-v1c-native-sensitivity.json \
  --v1b1 /tmp/spk-bv-v1b1-native-operator-replay.json \
  --v1a /tmp/spk-bv-v1a-symbolic-holdout.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --out /tmp/spk-bv-v1e-conditional-receiver-impact.json
```

## Next scientific gate

Attest actual directed route/source-to-recipient correspondence from frozen
network records; then define a **predeclared recipient assessment criterion**
owned by the recipient, and compare future network outcomes using the same
external goal and a paired OFF control. Native feedback **delivery** alone is
insufficient. No frozen-core rewrite, commit, or online self-modification may be
claimed before its own explicit gate.
