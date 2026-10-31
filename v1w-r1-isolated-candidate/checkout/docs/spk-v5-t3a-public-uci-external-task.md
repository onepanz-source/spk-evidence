# SPK/* V5-T3a — External task ingress, public dataset / shadow evaluation

**State:** executable adapter and adversarial gate. NOT a blind RL result. No original UCI data were accessible in the cloud build environment; the included JSON reference is a deliberately **engineered self-test**, not a measurement on UCI.

## What changes scientifically

Prior T2c–T2h drew downstream demand in the experimenter's synthetic environment. V5-T3a introduces an **external, independently published task definition**: office occupancy recorded with photographic reference labels, and timestamped light and CO₂ sensors. The source is:

- Luis Candanedo, *Occupancy Detection*, UCI Machine Learning Repository (2016), DOI **10.24432/C5X01N**.
- Official source: https://archive.ics.uci.edu/dataset/357/occupancy-detection
- License: **CC BY 4.0**; cite source in downstream results.
- Official files: `datatraining.txt` (training/pilot) and `datatest2.txt` (future public evaluation). `datatest.txt` is reserved as an unused validation source in this iteration.

Do not confuse the origin of published photo labels with a secured holdout: the dataset is **public**. The labels are not blinded from researchers. There is no distinct external custodian. No scientific T3 GO is possible on this evidence alone.

## Fixed task mapping, frozen BEFORE reading the dataset

One source row is a separate episode: state resets, native A1b executes **one** program chosen for that row. Photo-derived `Occupancy` is *never an input of A or B*.

1. If `Light >= 200` lux: present contextual spike `C0` to A at `t`. Otherwise `C1` at `t`.
2. If `CO2 >= 600` ppm: present `P` at `t+1`. Otherwise no second event.
3. A may emit a spike. The fixed A1b network forwards through B to C.
4. At C, the independent **photo-derived occupancy reference** is presented at `t+5`, and an explicit closure at `t+6`.
5. The research observer sees one realized action's C reward (`+1` correct, `-1` incorrect). There is no reward for another unexecuted arm in the training step.

These fixed thresholds are intentionally crude. Photo labels are an **external oracle** injected into C for this research task, **NOT** C's autonomous environmental sensing. We cannot claim endogenous BV learning from this adapter, even if its observed-reward learner beats a baseline.

Three fixed candidate programs: `overemit` (baseline), `silent`, `temporal`; no modification of any native code. The training runner samples 180 chronological rows using **indices alone**, not target values. It uses balanced seeded exploration (one selected arm per row) and selects by mean observed reward. Evaluation uses 60 index-selected chronological rows from the separate `datatest2.txt`, after the pilot program has been fixed. Secondary auditor counterfactuals are calculated only **after** selection.

## Steps on fwork

Download the official Occupancy Detection ZIP from UCI, extract `datatraining.txt` and `datatest2.txt` into a local directory outside the SPK repository. Preserve the original source files. Do not use an arbitrary GitHub reupload as if it were source-authenticated.

```bash
cd ~/workspace/spk-backvalidation-v0
bash search/spk_v5_t3a_external_uci_gate.sh /tmp/spk-v5-t3a-selftest.json
python search/spk_v5_t3a_external_uci.py pilot \
  --data /path/to/uci/datatraining.txt \
  --out /tmp/spk-v5-t3a-uci-pilot.json
sha256sum /tmp/spk-v5-t3a-uci-pilot.json
# Copy the printed pilot SHA, WITHOUT altering the pilot certificate.
python search/spk_v5_t3a_external_uci.py evaluate \
  --data /path/to/uci/datatest2.txt \
  --pilot /tmp/spk-v5-t3a-uci-pilot.json \
  --pilot-sha256 YOUR_PILOT_SHA_FROM_ABOVE \
  --out /tmp/spk-v5-t3a-uci-public-evaluation.json
```

All reports are **create-only**; delete or choose NEW paths for reruns. Outputs under the repository, symlinks and noncanonical pilot certificates are refused. The pilot SHA supplied by the operator is a local pin, **not an independently retained cryptographic witness**. UCI source raw SHA values are reported and must be reviewed by an independent custodian before any stronger conclusion.

## What the gate establishes

- Actual A1b program execution on time-ordered, bounded episodes.
- Separation of the measured features from photo labels for the A/B inputs.
- Chronological separation of the future public evaluation from the pilot.
- Staged pilot certificate and evaluation with a required pilot SHA pin.
- Strict rejection of malformed CSV, label tamper, duplicate timestamps, overlapping splits, unsupported programs, forged rewards, stale SHA, unsafe output paths.
- Engineered self-test correct and reproducible, with **no external dataset falsely claimed**.

## Exclusions

- No independent *blind* evaluation, prepublished external test-only custody, or meaningful population-level statistical effect yet.
- No spontaneous local island task objective: labels come from external photographic annotation.
- No native BV inbound semantic control or neuron-local program learning.
- The source A1b evaluator uses ideal transport for this adapter; previously measured T2h integrated feedback costs are **not** charged by this public-data adapter. Any performance claim must reconcile that cost, and independent sessions/time blocks are statistical units, not individual sensor minutes.
- No frozen Core/Network/Compiler/Architecture or v0e scheduler changes. No performance victory or promotion implied by a synthetic positive control.

**Next:** run the official files on fwork. If results warrant continuation, design an actual holdout held by another authority, lock the analysis and costs before seeing results, and run feedback vs matching placebo and frozen baseline across independent source sessions. Even then, replacing a photographic oracle with *endogenous island evidence* remains a separate scientific problem.
