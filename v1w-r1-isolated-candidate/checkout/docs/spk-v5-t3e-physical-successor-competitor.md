# SPK V5-T3e. Real-successor A1b persistence vs strong current-only competitor

Status: **RESEARCH / public already inspected / no blind holdout / no native learning**.

## Question

Can a causal two-observation A1b program using actual minute-separated UCI readings improve over an **A1b current-only** rule on the independent photo-derived occupancy **state**, while respecting the same fixed 200-lux sensor threshold and label separation?

## Design

- `previous` and `current` refer to two different original UCI physical measurements with actual time difference **59, 60 or 61 seconds**. All other intervals are rejected/countable.
- Every raw file is parsed directly by the pinned T3b adapter, retaining its original SHA-256. No synthetic within-row tick offset.
- Sensor input to A consists only of the previous/current light-threshold state, never occupancy, photographic labels, source row indices or future readings.
- Four possible two-reading Boolean contexts are executed through the frozen Architecture A1b PE implementation, for the original `silent`, `overemit`/current, `temporal`/rise, plus an additive research-only `persist` program. The new program **does not modify** the frozen `PROGRAMS` registry.
- `current` means current light >= 200 lx; `persist` means previous light >= 200 lx **and** current light >= 200 lx. Both are native A1b programs. The simple two-reading Boolean implementation is an exact comparator, so this is a calculation/execution equivalence, not evidence of emergent intelligence.
- Photo-derived current occupancy is used by the host **only after** scoring sensor-only decisions. Training-only scores select between `current` and `persist` by balanced accuracy with a simplicity tie break (`current`). Public earlier and later cohorts are assessed after choice, and carry the warning that they have already been inspected in T3b/T3c/T3d.
- Actual 20,557 row-pairs are evaluated by the proven **four-class A1b truth table** (A1b run per input class), not by executing all 20,557 rows separately. This equivalence is explicit and testable. No resource or wall-clock profiling claim is made.
- Diagnostic fields: raw counts, confusion matrices, balanced accuracy, paired disagreements and per-day metrics. Per-minute observations and even adjacent days should not be treated as independent draws.

## Acceptance and scientific vetoes

1. Source/predecessor SHA pin, strict original CSV, chronology, create-only output, and immutable authority checks PASS.
2. Actual A1b relay and four-case truth table PASS. A tampered executor is rejected, and photo label mutation does not change sensor decisions.
3. Train selected arm is computed before public comparisons; C oracle and labels are not native generated/reverse delivered.
4. Any small gain/loss is presented descriptively. No p-values, confidence intervals based on independent minute samples, blind T3 claims or automatic program promotion.
5. T3f would require third-party holdout custody and/or genuinely new data, a proper forward validation, matched supervised baseline and native feedback source, not another pass over published labels.

No changes to Core, Network, Compiler, Architecture v1, BV v0e, or frozen V5 artifacts.
