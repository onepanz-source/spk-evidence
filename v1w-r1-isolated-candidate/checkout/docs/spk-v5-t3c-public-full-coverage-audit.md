# SPK V5-T3c — Public UCI full-coverage challenge audit (research)

## Motivation and non-promotion

T3b selected `temporal` from 180 *labelled* training episodes, then evaluated on 60 publicly available UCI Occupancy Detection rows. A genuine test of whether the benchmark demonstrates physical **temporal** computation must look at how those inputs were constructed. T3a emits channel C0 or C1 at tick `t` based on *one measured light reading* and P at tick `t+1` based on *the same row's measured CO₂ reading*. The one-tick difference was invented by the adapter; it was not measured from a subsequent real-world observation.

T3c **does not tune any candidate, thresholds or training procedure**. It replays frozen A1b on every original row of all three public UCI files and asserts exact equivalence:

- `temporal` ⇔ static `(Light ≥ 200 lux) ∧ (CO₂ ≥ 600 ppm)`
- `overemit` ⇔ static `(CO₂ ≥ 600 ppm)`
- `silent` ⇔ constant `False`

A mismatch is a **fatal audit error**, never repaired by redefining the labels or selecting a different policy. The original UCI row ID is not sent to the neuron; `Occupancy` is revealed only during auditor scoring. No source rows are bundled.

## Source splits, immutable decisions and provenance

- `datatraining.txt` is the original 8,143-row training file, used to reconstruct the original pilot byte-for-byte. Its **full-coverage** score is diagnostic and post-hoc, never an unseen test.
- `datatest.txt` (2,665 rows) is **chronologically before** training, so is an earlier-period challenge, **not** a forward-time holdout.
- `datatest2.txt` (9,752 rows) is **chronologically after** training. It is still a **public, nonblind** holdout. Reconstruct the previously published 60-row T3b report byte-for-byte before extending the audit.

Input SHA-256 is computed on exact original bytes. The CLI requires sealed, canonical T3b pilot and evaluation JSON and verifies that their content is reproduced by the supplied three sources. The resulting report records the input hashes and every program's full-sample confusion matrix, balanced accuracy, per-calendar-day breakdown, paired mistake disagreements, and eight **disjoint** interleaved 60-row diagnostic groups per split. The interleaved groups are *not independent time-series experiments*. Daily and sampled comparisons are descriptive; no p-values or independent-trial confidence claims are made.

All programs' post-selection scores are **auditor-only**: no counterfactual result is allowed to influence the sealed pilot. The 200/600 thresholds were fixed by T3a; T3c does not optimize them. Alternative sensor-only light threshold is a descriptive check, not an SPK candidate program.

## Run on fwork

```bash
cd ~/workspace/spk-backvalidation-v0
bash search/spk_v5_t3c_public_audit_gate.sh

PILOT=/tmp/spk-v5-t3b-uci-pilot.json
EVAL=/tmp/spk-v5-t3b-uci-public-eval.json
python search/spk_v5_t3c_public_full_coverage.py \
  --train ~/Scaricati/occupancy/datatraining.txt \
  --early ~/Scaricati/occupancy/datatest.txt \
  --late ~/Scaricati/occupancy/datatest2.txt \
  --pilot "$PILOT" --pilot-sha256 "$(sha256sum "$PILOT" | awk '{print $1}')" \
  --public-evaluation "$EVAL" --eval-sha256 "$(sha256sum "$EVAL" | awk '{print $1}')" \
  --out /tmp/spk-v5-t3c-original-uci-full-coverage.json

sha256sum /tmp/spk-v5-t3c-original-uci-full-coverage.json
```

The output file must not exist, must be outside the repository and must not be a symlink. The recorded pilot/evaluation are already public; checking their SHA-256 is integrity checking **not cryptographic independent custody**. There is no native learning, source adaptation, endpoint ownership change, native reverse BV delivery, or evidence of learned physical time dynamics. Frozen Core, Compiler, Architecture v1, BV v0e and all preceding V5 modules remain unchanged.

## Observed outcome on the uploaded authentic UCI sources

The pilot and public T3b report match their preceding published canonical hashes. The selected `temporal` program has 199/8,143 errors on the full training period, 106/2,665 on the earlier public period, and 666/9,752 on the later public period; `overemit` yields respectively 681, 429 and 4,071 errors; `silent` yields 1,729, 972 and 2,049 errors. A **post-hoc** plain light≥200-lux rule scores 367, **56**, and **414** errors. This rule was neither a candidate nor a frozen SPK neuron program, so it must not be represented as a registered comparator, but it **outperforms** the selected program in BOTH public test periods. Consequently, selecting the best of three deliberately limited programs does not prove superiority of the neuromorphic computation.

The measured calendar days include long zero-occupancy intervals and serial correlation; a repeated minute-level score is not an independent replicated physical experiment. These outcomes establish external-data program execution and a successful narrow three-arm selection; they **do not** show native learning, genuinely temporal physical computation, or an independently blinded reinforcement objective. The registered original 60-point T3b result remains unchanged.
