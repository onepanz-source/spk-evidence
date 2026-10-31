# SPK V5-T3f — calendar-stratified falsification of public T3e results

**Scope:** post-selection descriptive audit; NOT a new program, learning algorithm,
statistical generalization claim, native BV reward, or blind experiment.

**Data custody:** exactly original UCI `datatraining.txt`, `datatest.txt`,
`datatest2.txt`, validated by the additive T3b reader and matching frozen SHA-256.
The canonical T3e report is SHA-256 verified and its 3 cohort confusion totals and
source-grounded paired disagreement counts are independently reconciled.

**Native execution:** the four-pattern decision table is recomputed with the
frozen Architecture A1b executor through the research-only T3e programs. The
20,557 real consecutive minute-spaced input pairs are then classified with
that *verified* truth table; this is not per-row native reexecution. For
`current` versus `persist`, A1b predictions differ only when measured light
crosses from <200 to >=200 lux between two actual adjacent samples separated
by 59, 60, or 61 seconds. No label, calendar day, or future measurement is
sent to A. Labels become visible only after the decision, to the external auditor.

## Controlled questions

1. Is the +15 (persist minus current) difference driven by all-zero photo-label
   days? These group labels are **computed post hoc from photo-derived ground
   truth** and could not be used as an input or policy gate in deployment.
2. On days with any admitted occupied reading, does the effect persist?
3. How many physical dark-to-bright *opportunities* drive the difference?
4. Can each per-day and stratified aggregate be reconciled exactly with the
   original T3e reference? Can leaving out one entire calendar date flip the
   sign? The leave-one-out results are **descriptive diagnostics only**, not
   independent replicates or confidence estimates.

No parametric significance test, confidence bound, or data-driven model
selection is permitted from these already-inspected public data.

## Canonical original UCI audit

| Split | Pairs | current errors | persist errors | Net persist advantage | Zero-presence days | On days with occupancy |
|---|---:|---:|---:|---:|---:|---:|
| Train | 8,142 | 367 | 352 | +15 | +18 (2 days) | -3 (5 days) |
| Early public (BEFORE train) | 2,664 | 56 | 57 | -1 | 0 (0 days) | -1 (3 days) |
| Later public | 9,751 | 414 | 399 | +15 | +17 (2 days) | -2 (6 days) |

In later data the +17 on Saturday 2015-02-14 and Sunday 2015-02-15
accounts for all of the +15 aggregate. The remaining six calendar days
have a net -2. This also shows that the positive average alone was not a
reliable temporal-learning criterion. Day groups are neither independent
experiments nor a feature fed to the neuron.

**Scientific verdict:** T3e's arithmetic and A1b capability remain intact.
The broad advantage interpretation is falsified by contextual stratification.
The effect is a bounded static two-reading Boolean filter, selected by a
host-supervised process, with zero evidence for native self-computation updates
or endogenous reverse local BV reward. T3 blind remains BLOCKED.

**Install and gate:** `bash search/spk_v5_t3f_day_stratification_gate.sh /path/to/original/occupancy`.
This checks old/new SHA custody, dedicated adversarial tests, inherited tests,
frozen A1b+BV and exact report reproduction. No frozen files are altered.
