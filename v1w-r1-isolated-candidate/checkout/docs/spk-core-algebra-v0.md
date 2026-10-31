# SPK/Core Algebra v0

Status: DRAFT FORMALIZATION
Scope: SPK/Core unsigned integer event-driven semantics
Milestone: finite closure verified through syntactic depth <= 5

---

## 1. Purpose

SPK/Core Algebra v0 defines the semantic model, observable behavior,
algebraic identities, domain-dependent identities, and experimental
evidence currently established for the SPK/Core instruction set.

The guiding principle is:

> first derive the algebra, then train or compose the network.

The canonicalizer is an implementation of this specification.
It is not the specification itself.

---

# 2. Semantic universe U0

## 2.1 Core configuration

A Core configuration contains:

- state_bits
- fractional_bits

Let:

    SCALE = 2 ** fractional_bits

The persistent raw state is an unsigned integer:

    x in [0, MAX_RAW]

where:

    MAX_RAW = 2 ** state_bits - 1

Unless explicitly stated otherwise, the algebraic identities in this
document are interpreted over successful, non-overflowing executions.

Overflow behavior is therefore not silently identified with normal
execution behavior.

---

## 2.2 Event batches

Events are processed in timestamp batches.

For a batch at timestamp t:

    delta = t - previous_timestamp

All instructions executed for the same batch observe the same `delta`.

For each input channel c define:

    n_c = number of events on channel c in the current batch

Every ACC instruction referring to channel c observes the same n_c.

Therefore n_c and delta are batch variables, not fresh variables per
instruction.

This shared-variable property is semantically significant.

---

## 2.3 Persistent and transient state

Persistent state:

    x : unsigned raw integer

Transient state:

    g : boolean guard

At the beginning of each event batch:

    g = false

The raw state persists across batches.

The guard does not.

---

# 3. Instruction semantics

For one batch with shared delta and channel counts n_c:

## A-ACC-01 — ACC

For:

    ACC(weight=w, channel=c)

with w >= 0:

    x' = x + w * SCALE * n_c

subject to Core overflow rules.

The guard is unchanged.

---

## A-SHIFT-01 — ShiftDecay

For:

    ShiftDecay(bits_per_tick=k)

with k >= 0:

    x' = x >> (k * delta)

The guard is unchanged.

All ShiftDecay instructions in the same batch use the same delta.

---

## A-CMP-01 — CMP

For:

    CMP(threshold_raw=h)

the raw state is unchanged and:

    g' = (x >= h)

The previous guard value is overwritten.

---

## A-EMIT-01 — EMIT

For:

    EMIT(channel_out=c)

if:

    g = true

one output event is emitted on channel c at the current batch timestamp.

Otherwise no event is emitted.

Raw state and guard are unchanged.

---

## A-RESET-01 — RESET

For:

    RESET(value_raw=r)

if:

    g = true

then:

    x' = r

otherwise:

    x' = x

The guard is unchanged.

---

# 4. Observable semantics

For a program P and an input spike train I, define:

    Obs(P, I, x0)

as:

    (
        canonical output spike multiset,
        final_raw_state,
        final_guard
    )

Output event ordering within the same timestamp is not observable.

Multiplicity is observable.

Program equivalence in U0 is:

    P ≡ Q

iff they have equal observations for every admissible initial state and
input history in the semantic universe under consideration.

Important:

The current finite experimental closure does not yet prove this
universal quantification.

---

# 5. Semantic axioms

## A-BATCH-01 — Shared delta

Every ShiftDecay executed in one batch observes the same delta.

---

## A-BATCH-02 — Shared channel count

Every ACC(_, c) executed in one batch observes the same n_c.

This is essential.

Two ACC instructions on the same channel do not consume independent
event-count variables.

---

## A-GUARD-01 — Guard reset

At batch entry:

    g = false

---

## A-GUARD-02 — CMP overwrite

CMP overwrites the previous guard completely.

---

## A-OUTPUT-01 — Output multiset semantics

Events emitted at the same timestamp are observed as a multiset.

Ordering among them is not observable.

Multiplicity is preserved.

---

## A-STATE-01 — Unsigned state

Core raw state is unsigned.

Several threshold identities depend on the absence of negative states.

---

# 6. General algebraic laws

These laws follow from Core semantics within U0, subject to their stated
side conditions.

---

## L-GUARD-01 — Dead guard

If a CMP-generated guard is overwritten by another CMP before any
EMIT or RESET can consume it, the first guard value is unobservable.

Schematically:

    CMP(a); S; CMP(b)

where S contains no guard-consuming instruction,

may be reasoned about without preserving the first guard value.

This law underlies dead-CMP canonicalization.

---

## D-ZERO-02 — CMP1 / RESET0 zero barrier

For unsigned raw state:

    CMP(1); RESET(0)

maps every incoming raw state to zero.

Proof:

If x = 0:

    CMP(1) = false
    RESET does not execute
    x remains 0

If x >= 1:

    CMP(1) = true
    RESET executes
    x becomes 0

Therefore:

    x_after = 0

for every unsigned x.

The guard produced by CMP(1), however, may still encode information
about the incoming state.

Consequently preceding state transformations may be discarded only when
that guard becomes dead before being consumed.

Implementation:

    _remove_dead_state_before_zero_barrier

---



### Runtime overflow qualification for D-ZERO-02

This identity is not runtime-total for finite-width Core when
`OverflowError` is observable.

The state update removed before the zero barrier may itself overflow
before execution reaches the compare/reset sequence that would
otherwise make its value irrelevant.

Concrete counterexample:

    state_bits = 8
    fractional_bits = 0
    max_raw = 255

    initial_raw = 254
    n_0 = 2
    delta = 0

Source:

    ACC(1,0)
    CMP(1)
    RESET(0)
    CMP(1)

attempts:

    254 -> 256

and raises `OverflowError` at the ACC.

The rewritten target:

    CMP(1)
    RESET(0)
    CMP(1)

executes successfully and ends with:

    raw = 0
    guard = false

Therefore removing state updates before the zero barrier may remove an
observable overflow.

D-ZERO-02 is valid only inside the declared bounded
successful/non-overflowing synthesis domain in which both source and
rewritten executions remain defined. It is not a runtime-total
identity for arbitrary finite-width Core states.
## L-CTRL-01 — State-invariant CMP/EMIT trace

Inside a maximal run containing only CMP and EMIT instructions, raw
state does not change.

The observable behavior of the run is therefore determined by:

1. the multiset of emitted channels paired with the threshold controlling
   each emission;
2. the threshold of the final CMP, which determines final guard.

This permits canonical ordering of threshold/emission groups while
preserving:

- output multiplicity
- final raw state
- final guard

Implementation:

    _normalize_cmp_emit_runs

---

## L-CTRL-02 — Emit/reset threshold partition

For:

    r < a <= b

and identical emission channel c:

    CMP(b); EMIT(c); RESET(r); CMP(a); EMIT(c)

is equivalent to:

    CMP(a); EMIT(c); CMP(b); RESET(r); CMP(a)

Proof by state partition:

    x < a
    a <= x < b
    x >= b

Each region produces identical:

    emitted multiset,
    final state,
    final guard.

Implementation:

    _normalize_emit_reset_partition

---

# 7. Shared-count laws

These laws use A-BATCH-02 explicitly.

---

## L-COUNT-01 — CMP1 commute over repeated same-channel ACC

Assume a positive contribution from n_c has already entered the state:

    y = x + w*n_c + R

with:

    w > 0
    R >= 0

Then for v > 0:

    y >= 1

iff:

    y + v*n_c >= 1

Reason:

If y = 0, non-negativity implies:

    x = 0
    n_c = 0
    R = 0

and therefore the second ACC also contributes zero.

Thus, under the appropriate state-preservation conditions:

    ... ACC(w,c) ... CMP(1); ACC(v,c)

can be normalized to:

    ... ACC(w,c) ... ACC(v,c); CMP(1)

when both ACC instructions observe the same batch count n_c.

Implementation:

    _normalize_shared_count_cmp1_acc_commute

---

## D-COUNT-01 — Pre-shift repeated ACC elimination

For:

    w > 0
    v > 0
    k > 0

consider:

    ((x + w*n_c) >> (k*delta)) + v*n_c

and:

    (x >> (k*delta)) + v*n_c

Their positivity is identical.

Proof by cases.

If:

    n_c > 0

then:

    v*n_c > 0

so both expressions are positive.

If:

    n_c = 0

the expressions are identical.

Therefore before:

    CMP(1); RESET(...)

the first same-channel ACC is irrelevant to the branch decision:

    ACC(w,c);
    SHIFT(k);
    ACC(v,c);
    CMP(1);
    RESET(r)

may normalize to:

    SHIFT(k);
    ACC(v,c);
    CMP(1);
    RESET(r)

within the declared successful-execution domain.

Implementation:

    _normalize_shared_count_pre_shift_acc

---

# 8. Domain-dependent laws

These identities require stronger conditions than the base Core
semantics.

---



### Runtime overflow qualification for D-COUNT-01

This identity is not runtime-total for finite-width Core when overflow is
observable.

Concrete counterexample:

    state_bits = 8
    fractional_bits = 0
    max_raw = 255

    initial_raw = 254
    delta = 0
    n_0 = 1

Source:

    ACC(1,0)
    SHIFT(1)
    ACC(1,0)
    CMP(1)
    RESET(0)

executes:

    254 -> 255 -> 255 -> 256

and raises `OverflowError` on the second ACC.

The rewritten target:

    SHIFT(1)
    ACC(1,0)
    CMP(1)
    RESET(0)

executes successfully:

    254 -> 254 -> 255 -> 0

Therefore the rewrite may remove an observable overflow.

D-COUNT-01 is valid only inside the declared bounded
successful/non-overflowing synthesis domain in which both the source
and rewritten executions remain defined. It is not a runtime-total
identity for arbitrary finite-width Core states.
## D-ACC-01 — Positive ACC saturation before CMP1 / RESET0

For unsigned state and positive w:

    x + w*n_c >= 1

iff:

    x + n_c >= 1

Therefore a positive ACC weight may normalize to 1 when:

1. it is immediately relevant to CMP(1);
2. the resulting true-branch state difference is destroyed by RESET(0);
3. the guard is not overwritten before that reset;
4. execution is within the declared non-overflowing domain.

Implementation:

    _normalize_positive_acc_before_cmp1_zero_reset

This is not currently claimed as an overflow-preserving identity.

---

## D-TIME-01 — Positive shift widths on state {0,1}

For:

    x in {0,1}
    k >= 1

all positive ShiftDecay widths are equivalent with respect to x:

If:

    delta = 0

then:

    x >> (k*delta) = x

If:

    delta > 0

then:

    x >> (k*delta) = 0

Therefore on state bounded by one:

    ShiftDecay(k)

for every positive k may be normalized to:

    ShiftDecay(1)

Implementation:

    _normalize_temporal_shift_width

---

## L-TIME-08 — CMP2 temporal zero barrier

The canonicalizer contains temporal identities combining:

    CMP(2)
    ShiftDecay
    RESET(0)

that depend on:

- unsigned state;
- monotonic right shift;
- shared delta;
- threshold-derived bounds;
- eventual zero reset.

Implementation:

    _normalize_temporal_cmp2_barrier

These identities require individual proof obligations and remain
classified as domain-dependent until those proofs are recorded
separately.

---

## L-TIME-09 — Guarded reset / shift commute

Certain:

    CMP(2)
    EMIT*
    ShiftDecay
    RESET(0)
    CMP(2)

patterns permit moving ShiftDecay across the reset/control boundary.

The proof depends on the false branch being bounded below threshold 2
and the true branch being annihilated by RESET(0).

Implementation:

    _normalize_temporal_guarded_reset_commute

---


# 8A. Structural canonicalization laws

The historical structural canonicalizer implements the following
algebraic laws.

The term "structural" describes the implementation layer only.
Epistemic status is expressed by the Rule ID prefix:

    L-* = proved law in U0
    D-* = domain-dependent law

## L-ACC-01 — Zero accumulation

    ACC(0,c) ≡ epsilon

Implementation:

    _remove_zero_acc


## L-ACC-02 — Consecutive ACC commutation

For consecutive additive updates:

    ACC(a,c1); ACC(b,c2)
        ≡
    ACC(b,c2); ACC(a,c1)

provided both executions remain in the declared successful
non-overflowing Core domain.

Implementation:

    _normalize_acc_runs


## L-ACC-03 — Same-channel ACC fusion

    ACC(a,c); ACC(b,c)
        ≡
    ACC(a+b,c)

Implementation:

    _normalize_acc_runs


## L-GUARD-02 — Initial false-guard elimination

At batch entry the guard is False.

Therefore EMIT and RESET preceding the first CMP are inactive and may
be removed.

Implementation:

    _remove_false_guard_prefix


## L-EMIT-01 — EMIT commutation across guard-neutral state operations

EMIT reads guard but does not inspect or alter raw state.

ACC, RESET and ShiftDecay do not alter guard.

Therefore EMIT may commute across those operations, but not across CMP.

Implementation:

    _move_emit_left


## L-EMIT-02 — Coincident EMIT permutation

Adjacent EMIT instructions at the same batch timestamp may be ordered
canonically because output ordering is not observable and multiplicity
is preserved.

Implementation:

    _sort_emit_runs


## L-RESET-01 — Adjacent reset collapse

    RESET(a); RESET(b)
        ≡
    RESET(b)

because both resets observe the same guard.

Implementation:

    _collapse_adjacent_resets


## L-TIME-01 — Zero-reset / shift commute

    RESET(0); SHIFT(k)
        ≡
    SHIFT(k); RESET(0)

Implementation:

    _commute_zero_reset_across_shift


## L-TIME-02 — Shift elimination under CMP1 / RESET0

Within:

    CMP(1); [EMIT|SHIFT]*; RESET(0)

every intervening ShiftDecay is semantically redundant.

Implementation:

    _remove_shift_between_cmp1_and_reset0


## L-TIME-03 — Shift identity on known zero state

If:

    raw == 0

then every ShiftDecay preserves raw zero.

Implementation:

    _remove_shift_when_state_known_zero


## D-TIME-05 — Pre-ACC shift elimination under CMP1 / RESET0

In:

    CMP(1); SHIFT*; ... ACC ...; RESET(0)

ShiftDecay instructions before the first ACC are algebraically
irrelevant to the eventual successful final state when no CMP
overwrites the controlling guard before RESET(0).

However this is NOT a runtime-total identity in finite-width Core.

Removing the shift can increase the raw value reaching a later ACC and
therefore expose an OverflowError before RESET(0) can annihilate the
state.

Concrete counterexample for:

    state_bits = 8
    fractional_bits = 0
    max_raw = 255

with:

    initial_raw = 254
    delta = 1
    n_0 = 2

Source:

    CMP(1)
    SHIFT(1)
    ACC(1,0)
    RESET(0)

executes successfully:

    254 -> 127 -> 129 -> 0

while the rewritten target:

    CMP(1)
    ACC(1,0)
    RESET(0)

attempts:

    254 -> 256

and raises OverflowError.

Therefore this rewrite is valid only in a declared bounded
non-overflowing synthesis domain that guarantees the rewritten
intermediate ACC values remain representable.

It is not currently runtime-safe for arbitrary Core inputs.

Implementation:

    _remove_pre_acc_shift_under_cmp1_reset0


## L-TIME-05 — Known-false compare / shift sinking

    CMP(t); RESET(0); CMP(t); SHIFT(k)

may normalize to:

    CMP(t); SHIFT(k); RESET(0); CMP(t)

because after the first CMP/RESET pair the state is strictly below t
and unsigned right shift preserves that bound.

Implementation:

    _sink_known_false_compare_across_shift


## L-TIME-06 — Consecutive shift fusion

    SHIFT(a); SHIFT(b)
        ≡
    SHIFT(a+b)

because all shifts in the batch observe the same delta and:

    (x >> (a*delta)) >> (b*delta)
        =
    x >> ((a+b)*delta)

Also:

    SHIFT(0) ≡ epsilon

Implementation:

    _normalize_shift_decay_runs


## L-TIME-07 — Compare-bound shift saturation

For:

    CMP(t); SHIFT(k); RESET(0)

the false branch establishes:

    0 <= raw < t

Let:

    m = bit_length(t - 1)

All positive shift widths k >= m are equivalent on that bounded branch,
while RESET(0) annihilates the true branch.

Therefore such k may canonicalize to m.

Implementation:

    _cap_shift_before_zero_reset_from_compare_bound


## L-CMP-01 — Redundant repeated comparison

If raw state has not changed:

    CMP(t); G; CMP(t)

where G preserves raw state, the second comparison is redundant.

Implementation:

    _remove_redundant_repeated_compares


## L-CMP-02 — Proven-false compare after guarded reset

For:

    CMP(a); EMIT*; RESET(r); CMP(b)

with:

    r < a
    b >= a

the final comparison is always False and may canonicalize to CMP(a).

Implementation:

    _normalize_false_compare_after_reset


## L-GUARD-03 — Dead consumers after proven-false compare

When L-CMP-02 establishes a certainly False final guard, immediately
following EMIT and RESET instructions are inactive and may be removed.

Implementation:

    _normalize_false_compare_after_reset


## D-RESET-01 — Shadowed reset elimination

    RESET(a); X; RESET(b)
        -> X; RESET(b)

when X contains no CMP.

This identity is classified as domain-dependent because removing the
first reset may expose intermediate ACC overflow behavior that is absent
from the successful non-overflowing algebraic domain.

Implementation:

    _remove_shadowed_resets


## L-ACC-04 — Saturated same-channel ACC pull across compare

If a pre-CMP ACC(a,c) already guarantees CMP(theta)=True whenever
n_c > 0, then a later same-channel ACC may be moved before that compare
and fused with the saturating witness.

The law depends on:

    unsigned raw state
    shared batch count n_c
    positive threshold

Implementation:

    _pull_saturated_acc_across_compare


## D-ACC-03 — Saturated ACC cap before guarded reset

When a single event on c already saturates CMP(theta), and the true
branch ends in RESET, weight above the minimum saturating value is
unobservable in the declared successful-execution domain.

Implementation:

    _cap_saturated_acc_before_guarded_reset


## D-ZERO-01 — LSB annihilator dead-state elimination

The sequence:

    CMP(1); RESET(0); CMP(1)

always terminates with:

    raw   = 0
    guard = False

Therefore an immediately preceding state-only update may be dead.

The identity is classified as domain-dependent because elimination of an
ACC may change observable overflow behavior outside the current
successful-execution domain.

Implementation:

    _strip_state_before_lsb_annihilator


# 9. Rule-to-implementation map

| Rule | Implementation |
|---|---|
| L-ACC-01 | `_remove_zero_acc` |
| L-ACC-02 | `_normalize_acc_runs` |
| L-ACC-03 | `_normalize_acc_runs` |
| L-GUARD-01 | `_remove_dead_compares` |
| L-GUARD-02 | `_remove_false_guard_prefix` |
| L-GUARD-03 | `_normalize_false_compare_after_reset` |
| L-EMIT-01 | `_move_emit_left` |
| L-EMIT-02 | `_sort_emit_runs` |
| L-RESET-01 | `_collapse_adjacent_resets` |
| L-TIME-01 | `_commute_zero_reset_across_shift` |
| L-TIME-02 | `_remove_shift_between_cmp1_and_reset0` |
| L-TIME-03 | `_remove_shift_when_state_known_zero` |
| D-TIME-05 | `_remove_pre_acc_shift_under_cmp1_reset0` |
| L-TIME-05 | `_sink_known_false_compare_across_shift` |
| L-TIME-06 | `_normalize_shift_decay_runs` |
| L-TIME-07 | `_cap_shift_before_zero_reset_from_compare_bound` |
| L-CMP-01 | `_remove_redundant_repeated_compares` |
| L-CMP-02 | `_normalize_false_compare_after_reset` |
| D-RESET-01 | `_remove_shadowed_resets` |
| L-ACC-04 | `_pull_saturated_acc_across_compare` |
| D-ACC-03 | `_cap_saturated_acc_before_guarded_reset` |
| D-ZERO-01 | `_strip_state_before_lsb_annihilator` |
| D-ZERO-02 | `_remove_dead_state_before_zero_barrier` |
| L-CTRL-01 | `_normalize_cmp_emit_runs` |
| L-CTRL-02 | `_normalize_emit_reset_partition` |
| L-COUNT-01 | `_normalize_shared_count_cmp1_acc_commute` |
| D-COUNT-01 | `_normalize_shared_count_pre_shift_acc` |
| D-ACC-01 | `_normalize_positive_acc_before_cmp1_zero_reset` |
| D-TIME-01 | `_normalize_temporal_shift_width` |
| L-TIME-08 | `_normalize_temporal_cmp2_barrier` |
| L-TIME-09 | `_normalize_temporal_guarded_reset_commute` |

`canonicalize_core_program`, `abstract_normalize_once`,
`abstract_normalize_program`, and
`canonicalize_core_program_semantic` are orchestration procedures and
do not receive algebraic Rule IDs.

`_acc_channel_key` is an implementation helper and does not receive an
algebraic Rule ID.


# 10. Experimental evidence

## E-D5-01 — Depth <= 5 syntax domain

Instruction pool size:

    7

Program lengths:

    1 .. 5

Total syntactic programs:

    19607

---

## E-D5-02 — Structural canonicalization

Structural canonical forms:

    2404

---

## E-D5-03 — Semantic canonicalization

Semantic canonical forms:

    2365

---

## E-D5-04 — Observed behavioral quotient

Observed behavioral classes:

    2365

Therefore on the declared depth-5 experiment:

    19607 -> 2404 -> 2365 -> 2365

and:

    semantic canonical forms
        =
    observed behavioral classes

Residual classes:

    0

Residual excess:

    0

This result is called:

    SPK/Core Algebra v0 finite closure through depth 5

It is not currently a theorem of universal completeness.

---

## E-D5-05 — Preservation experiment

Refined observational samples:

    442

All:

    19607

syntactic programs were checked against their semantic canonical form.

Observed preservation violations:

    0

Therefore preservation is:

    EXACT ON THE REFINED FINITE CORPUS

This statement must not be silently strengthened to universal semantic
equivalence.

---

# 11. Epistemic status

SPK/Core Algebra v0 currently contains four distinct classes of claims.

## AXIOM

Defines Core semantics.

Examples:

    shared delta
    shared channel count
    unsigned state
    guard reset
    instruction semantics

## PROVED LAW

Derived directly from the axioms with explicit side conditions.

Examples currently include:

    CMP1 / RESET0 zero barrier
    state-invariant CMP/EMIT traces
    threshold partition identity
    shared-count positivity identities

## DOMAIN LAW

Proved only under additional restrictions.

Examples:

    non-overflow execution
    state bounded by {0,1}
    specific thresholds
    positive weights
    unsigned monotonic shift

## EXPERIMENTAL RESULT

Established by finite enumeration/testing.

Examples:

    depth-5 closure
    2365 observed behavioral classes
    zero residuals
    preservation on the 442-sample corpus

These categories must remain separate.

---

# 12. What is NOT yet claimed

Algebra v0 does not yet claim:

- universal completeness at arbitrary program depth;
- equivalence preservation when overflow exceptions are observable;
- completeness for arbitrary instruction parameters;
- compositional congruence across networks of Core nodes;
- completeness for future Core instructions;
- equivalence under IEEE floating-point SPK semantics;
- correctness of the abstract interpreter for every concrete state.

---

# 13. Formalization gates remaining

Before declaring SPK/Core Algebra v0 complete:

1. catalogue all structural canonicalization rules;
2. give every rewrite a stable Rule ID;
3. complete proof sketches / proof obligations for every semantic rule;
4. validate abstract interpretation against concrete execution;
5. build an independent rule-level soundness checker;
6. run the checker on a domain wider than the discovery corpus;
7. freeze the v0 specification and implementation mapping.

Only after these gates should the project move to network composition
or depth-6 discovery.

---

# 14. Next soundness domain

Initial independent validation target:

    x0      = 0 .. 64
    n0      = 0 .. 3
    n1      = 0 .. 3
    n2      = 0 .. 3
    delta   = 0 .. 6

The rule-level checker must compare:

    (
        output,
        final_raw,
        final_guard
    )

for both sides of every instantiated rewrite.

The checker must not reuse the 442-sample discovery corpus as its sole
oracle.

---

# 15. Current milestone

SPK/Core semantic canonicalization has reached finite closure through
depth 5 on the declared experimental domain:

    19607 syntactic
        ->
    2404 structural canonical
        ->
    2365 semantic canonical
        =
    2365 observed behavioral classes

with:

    residual classes = 0
    residual excess = 0

This is the starting point for formalization, not the end of it.

# F0.3 — Independent soundness evidence

The finite closure experiments are complemented by independent
soundness gates that do not use the depth-5 behavioral corpus as their
oracle.

These gates provide empirical evidence. They do not constitute a
universal completeness or soundness proof.

## Abstract Soundness Evidence A0

The abstract interpreter was checked instruction-by-instruction against
an independent concrete interpreter.

Domains exercised included:

- initial raw states `0..64`;
- channel counts `n_0,n_1,n_2 = 0..3`;
- temporal deltas `0..6`;
- systematic programs through depth 3;
- explicit states near `max_raw`.

Final checkpoint:

    program instances checked: 1602
    concrete executions: 6772193
    concrete instruction states checked: 19534498
    overflowing executions skipped: 1820
    abstract soundness violations: 0

For every successful concrete prefix tested, the concrete pair

    (raw, guard)

was contained in the abstract `GuardPartition` produced after the same
instruction.

This result is recorded as:

    Abstract Soundness Evidence A0

It is finite empirical evidence, not a proof for all Core programs or
configurations.

## Rule Soundness Evidence R0

All 29 implementation rewrite functions corresponding to the 31
algebraic Rule IDs were exercised directly.

Rules not activated by the original depth-5 syntax pool were supplied
with explicit activation witnesses. Therefore every rewrite function
had:

    changed_programs > 0

The concrete checker treats finite-width overflow as observable.

For runtime laws `L-*`, the required condition is:

    source terminates successfully
        iff
    rewritten target terminates successfully

and whenever both executions terminate:

    Obs(source) = Obs(target)

where:

    Obs(P) =
        (
            output multiset,
            final raw state,
            final guard,
            last timestamp
        )

For domain laws `D-*`, equivalence is claimed only where both source and
rewritten executions remain inside the declared successful,
non-overflowing synthesis domain:

    source successful
    and target successful
        implies
    Obs(source) = Obs(target)

Departures from that domain are counted explicitly and are not treated
as successful runtime equivalences.

Final checkpoint:

    rewrite helpers checked: 29
    changed source programs: 42222
    concrete observation cases: 16044360

    source overflow cases observed: 579049
    matched runtime overflow cases: 542509

    runtime source-overflow removals: 0
    runtime target-overflow failures: 0

    declared domain source exclusions: 36540
    declared domain target escapes: 1455

    observation mismatches: 0

Result:

    RULE SOUNDNESS CHECKPOINT:
        PASS WITH DECLARED DOMAIN EXCLUSIONS

This result is recorded as:

    Rule Soundness Evidence R0

## Overflow observability and dead execution

The soundness campaign exposed an important semantic distinction:

    dead value != dead execution

A state value that will later be overwritten, reset, shifted away, or
otherwise become observationally irrelevant is not necessarily safe to
remove.

The computation producing that value can itself remain observable
through finite-width `OverflowError`.

Three rules originally classified more strongly were reclassified after
concrete counterexamples:

    D-TIME-05
        _remove_pre_acc_shift_under_cmp1_reset0

        Removing a pre-ACC shift can introduce an overflow that the
        source avoided.

    D-COUNT-01
        _normalize_shared_count_pre_shift_acc

        Removing a repeated same-channel ACC can remove an overflow
        observable in the source.

    D-ZERO-02
        _remove_dead_state_before_zero_barrier

        Removing state computation before a later zero barrier can
        remove an overflow occurring before the barrier is reached.

Therefore finite-width overflow is part of the operational
observability boundary of SPK/Core v0.

## F0.3 status

The following independent gates are now satisfied:

    formal rule coverage:
        31 Rule IDs
        29 rewrite functions
        1 helper
        4 orchestrators
        0 unclassified
        0 stale mappings

    abstract soundness evidence:
        A0 PASS

    rule-level soundness evidence:
        R0 PASS WITH DECLARED DOMAIN EXCLUSIONS

    depth-5 finite semantic closure:
        19607 syntactic programs
        2365 semantic canonical programs
        2365 behavioral classes
        0 ambiguous classes
        0 residual excess

These results establish a finite, explicitly scoped validation of
SPK/Core Algebra v0.

They do not establish universal completeness or universal soundness
outside the declared semantic and finite-width domains.
