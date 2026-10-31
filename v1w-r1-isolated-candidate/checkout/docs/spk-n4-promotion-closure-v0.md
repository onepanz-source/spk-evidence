# SPK N4 Promotion Closure — Phase 1 Complete

Date: 2026-10-12

## Scope

This checkpoint closes the five N4 DOMAIN-to-RUNTIME promotion
candidates.

Closure does not require every candidate to become a runtime law.
A candidate is closed when it has either:

- a runtime-safe local proof, or
- an explicit counterexample and a rigorous DOMAIN condition.

## Final candidate disposition

### L-ACC-04

Historical candidate:

    D-ACC-02

Implementation:

    _pull_saturated_acc_across_compare

Result:

    PROMOTED TO RUNTIME

Reason:

Unsigned non-negative ACC semantics and shared batch counts guarantee
the comparison whenever the saturating witness channel is present.

Moving the later same-channel contribution earlier preserves guard,
EMIT behavior, final state and overflow definedness.


### L-TIME-07

Historical candidate:

    D-TIME-04

Implementation:

    _cap_shift_before_zero_reset_from_compare_bound

Result:

    PROMOTED TO RUNTIME

Reason:

The false CMP branch bounds raw below the threshold. Once shift width
reaches bit_length(threshold - 1), every positive-delta execution maps
that entire interval to zero. RESET(0) annihilates the true branch.


### L-TIME-08

Historical candidate:

    D-TIME-02

Implementation:

    _normalize_temporal_cmp2_barrier

Result:

    PROMOTED TO RUNTIME

Reason:

The CMP(2)/SHIFT/RESET(0) barrier maps the relevant state either to
{0,1} for delta == 0 or to zero for delta > 0. The trailing CMP
overwrites intermediate guard differences.

No transformed instruction introduces asymmetric overflow.


### L-TIME-09

Historical candidate:

    D-TIME-03

Implementation:

    _normalize_temporal_guarded_reset_commute

Result:

    PROMOTED TO RUNTIME

Reason:

On the true branch RESET(0) destroys the shifted value.

On the false branch CMP(2) proves raw in {0,1}, so the second CMP(2)
remains false on either orientation.

Intervening EMIT instructions observe the same guard.

No asymmetric overflow is introduced.


### D-TIME-01

Implementation:

    _normalize_temporal_shift_width

Result:

    REMAINS DOMAIN

The original guarded-reset matcher allowed ACC instructions between
SHIFT and RESET(0).

That condition is not runtime-safe.

Counterexample on 8-bit unsigned Core:

    initial_raw = 255
    delta       = 1

Source:

    CMP(2)
    SHIFT(2)
    ACC(129, c0)
    RESET(0)

Source execution:

    255 >> 2 = 63
    63 + 129 = 192

and is defined.

Rewriting SHIFT(2) to SHIFT(1) gives:

    255 >> 1 = 127
    127 + 129 = 256

which overflows.

Therefore:

    defined(source) != defined(target)

and the original candidate cannot be promoted.

The matcher was narrowed so that only EMIT instructions may occur
between the shift and the safe RESET(0) in the guard-partitioned case.

The corrected rule remains DOMAIN because its applicability depends on
the abstract interpreter proving the required raw-state bound.

Finite stress evidence supports the corrected matcher but is not
treated as a universal proof of abstract-analysis soundness.


## Registry after Phase 1

    rule specs: 29
    Rule IDs: 31

    runtime helpers: 21
    domain helpers: 8

    Core runtime helpers: 16
    Core domain helpers: 4

    semantic runtime helpers: 5
    semantic domain helpers: 4


## Remaining DOMAIN rules

Core:

    D-ACC-03
    D-RESET-01
    D-TIME-05
    D-ZERO-01

Semantic:

    D-ACC-01
    D-COUNT-01
    D-TIME-01
    D-ZERO-02


## Soundness checkpoint

    changed source programs:       42,222
    concrete observation cases:    16,044,360
    source overflow cases:         579,049
    matched runtime overflow:      553,085

    runtime overflow removals:           0
    runtime target overflow failures:    0

    DOMAIN source exclusions:       25,964
    DOMAIN target escapes:           1,455

    observation mismatches:              0


## Runtime profile equivalence

Core runtime:

    programs: 7380
    mismatches: 0

Semantic runtime:

    programs: 7380
    Core DOMAIN helpers: 4
    semantic DOMAIN helpers: 4
    mismatches: 0


## Runtime quotient

    source programs:       7380
    runtime Core classes:   734
    joint classes:          598

    additional temporal collapse: 136

    cycles:                  0
    idempotence failures:    0
    observation mismatches:  0
    overflow asymmetries:    0
    runtime quotient splits: 0


## Phase 1 conclusion

The five promotion candidates are closed:

    promoted to runtime: 4
    retained as DOMAIN:  1

D-TIME-01 was not silently accepted after finite testing. Its original
condition was refuted by an explicit overflow counterexample, narrowed,
regression-tested, and retained as a conditional law.

Next phase:

    formalize executable Gamma_r premises for the eight remaining
    DOMAIN rules and prevent every DOMAIN rewrite from firing outside
    its declared validity region.
