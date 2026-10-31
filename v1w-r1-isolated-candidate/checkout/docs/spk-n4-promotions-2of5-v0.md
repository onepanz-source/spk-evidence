# SPK N4 Runtime Promotion Checkpoint — 2/5

Date: 2026-10-12

## Status

Two of the five N4 DOMAIN-to-RUNTIME promotion candidates have been
closed by local algebraic argument and integrated into the production
runtime canonicalization profile.

Promotions:

    D-ACC-02  -> L-ACC-04
    D-TIME-04 -> L-TIME-07


## L-ACC-04 — Saturated same-channel ACC pull

Implementation:

    _pull_saturated_acc_across_compare

Given a same-channel ACC(a,c) immediately before CMP(theta), with:

    theta > 0
    a * scale >= theta

a following ACC(b,c) in the allowed post-CMP ACC run may be pulled
before the comparison and fused with ACC(a,c).

For shared batch count n_c:

    n_c == 0

makes both moved contributions zero.

For:

    n_c > 0

ACC(a,c) already guarantees the comparison is true because the raw
state is unsigned and:

    n_c * a * scale >= a * scale >= theta.

Moving the later non-negative ACC contribution cannot therefore alter
the guard or intervening EMIT observations.

The total accumulated contribution is unchanged.

Because ACC contributions are monotone and non-negative, moving the
contribution earlier also preserves overflow definedness:

    Overflow(lhs) iff Overflow(rhs)

Therefore the law is runtime-safe under the declared Core semantics.


## L-TIME-07 — Compare-bound shift saturation

Implementation:

    _cap_shift_before_zero_reset_from_compare_bound

For:

    CMP(t); EMIT*; SHIFT(k); EMIT*; RESET(0)

with:

    t > 1

let:

    m = bit_length(t - 1).

On the false CMP branch:

    0 <= raw < t
    raw <= t - 1 < 2^m.

For delta == 0, both SHIFT(k) and SHIFT(m) are identities.

For delta > 0, every k >= m maps the complete false-branch interval
to zero.

On the true branch, RESET(0) destroys the shifted state.

CMP, EMIT, SHIFT and RESET(0) introduce no asymmetric overflow
behavior for this transformation.

Therefore:

    Obs(lhs) = Obs(rhs)

and:

    Overflow(lhs) iff Overflow(rhs).

The law is runtime-safe under the declared Core semantics.


## Registry state

After promotion:

    rule specs: 29
    Rule IDs: 31

    runtime helpers: 19
    domain helpers: 10

    Core runtime helpers: 16
    Core domain helpers: 4

    semantic runtime helpers: 3
    semantic domain helpers: 6


## Finite soundness gate

Declared R0 corpus:

    changed source programs:      42,222
    concrete observation cases:   16,044,360

    source overflow cases:        579,049
    matched runtime overflow:     553,060

    runtime overflow removals:          0
    runtime target overflow failures:   0

    DOMAIN source exclusions:      25,989
    DOMAIN target escapes:          1,455

    observation mismatches:             0


## Runtime profile equivalence

Core runtime profile:

    programs: 7380
    mismatches: 0

Semantic runtime profile:

    programs: 7380
    Core DOMAIN helpers: 4
    semantic DOMAIN helpers: 6
    mismatches: 0


## Runtime quotient after promotion

Before promotion, N4:

    7380 -> 744 -> 608

After promotion:

    7380 -> 734 -> 598

Runtime Core:

    classes: 734
    observation mismatches: 0
    overflow asymmetries: 0
    successful mismatches: 0

Joint Core + temporal:

    classes: 598
    additional temporal collapse: 136

    maximum rounds: 3
    cycles: 0
    idempotence failures: 0

    observation mismatches: 0
    overflow asymmetries: 0
    successful mismatches: 0

Quotient relation:

    runtime Core classes split by joint: 0
    joint classes merging Core classes: 79

Thus the two promoted Core laws remove ten additional runtime
equivalence classes without disturbing the previously observed
temporal collapse structure on the declared corpus.


## Epistemic boundary

The promotion of L-ACC-04 and L-TIME-07 is supported by local
algebraic arguments plus the existing finite soundness and quotient
gates.

The complete SPK Core Algebra v0 is not yet frozen.

Three N4 promotion candidates remain:

    D-TIME-01
    D-TIME-02
    D-TIME-03

They remain DOMAIN rules until separately closed.


## Next step

Derive local laws and overflow-preservation arguments for:

    _normalize_temporal_shift_width
    _normalize_temporal_cmp2_barrier
    _normalize_temporal_guarded_reset_commute
