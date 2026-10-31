# SPK N4 Runtime/Domain Algebra Checkpoint v0

Date: 2026-10-11

## Status

N4 establishes an explicit separation between runtime-safe rewrite rules
and domain-dependent rewrite rules in the SPK Core canonicalization system.

This checkpoint freezes the experimental and architectural state before
formal derivation of executable domain premises Gamma_r.

The checkpoint is reproduced by:

    ./search/n4_final_gate_v0.sh

A successful run ends with:

    N4 FINAL CHECKPOINT: PASS


## 1. Rule architecture

The rewrite system is partitioned as:

    R = L union D

where:

- L contains rules currently classified as runtime-safe;
- D contains rules whose current soundness claim is restricted to a
  successful bounded domain.

The rule registry contains:

    rewrite helpers: 29
    Rule IDs:        31

Current helper classification:

    runtime helpers: 17
    domain helpers:  12

Layer distribution:

    Core runtime helpers:      14
    Core domain helpers:        6

    Semantic runtime helpers:   3
    Semantic domain helpers:    6


## 2. Runtime canonicalization profiles

Two explicit runtime APIs now exist:

    canonicalize_core_program_runtime(...)

and:

    canonicalize_core_program_semantic_runtime(...)

The runtime profile structurally disables DOMAIN rules.

The profile propagates through the canonicalization stack, including
semantic canonicalization calling Core canonicalization.

This replaces the previous experimental monkeypatch mechanism.


## 3. Runtime profile equivalence

Core runtime profile equivalence:

    programs checked:    7380
    profile mismatches:     0

Semantic runtime profile equivalence:

    programs checked:          7380
    Core DOMAIN helpers:          6
    semantic DOMAIN helpers:      6
    profile mismatches:            0

Therefore the production runtime-profile APIs reproduce the previous
experimental runtime-only oracle over the declared 7380-program corpus.


## 4. Runtime Core quotient

Declared source corpus:

    source programs: 7380

Runtime Core normal forms:

    runtime Core classes: 744

Concrete observation cases:

    2,656,800

Observed failures:

    observation mismatches: 0
    overflow asymmetries:   0
    successful mismatches:  0


## 5. Runtime Core + temporal quotient

Joint normal forms:

    608

Additional collapse relative to runtime Core:

    136

Convergence:

    maximum rounds:       3
    cycles:               0
    idempotence failures: 0

Concrete observation cases:

    2,656,800

Observed failures:

    observation mismatches: 0
    overflow asymmetries:   0
    successful mismatches:  0

Quotient relation:

    runtime Core classes split by joint: 0

Joint classes merging runtime Core classes:

    79

Merge-size distribution:

    size 2: 39
    size 3: 29
    size 4:  6
    size 5:  4
    size 6:  1

Thus, on the declared corpus:

    7380 -> 744 -> 608

with no observed semantic split.


## 6. Rule soundness checkpoint

Rule soundness checked:

    rewrite helpers:             29
    changed source programs:  42222
    concrete observation cases: 16044360

Overflow observations:

    source overflow cases:            579049
    matched runtime overflow cases:   542509

Runtime-rule failures:

    source-overflow removals: 0
    target-overflow failures: 0

Domain exclusions:

    source exclusions: 36540
    target escapes:      1455

Observation mismatches:

    0

Status:

    PASS WITH DECLARED DOMAIN EXCLUSIONS


## 7. Exact meaning of the current DOMAIN classification

The current R0 harness does not yet implement explicit rule premises
Gamma_r.

For a DOMAIN rule, the existing harness excludes source executions that
overflow and also excludes cases where the rewritten target overflows.

Therefore the empirical D-rule claim at this checkpoint is:

    whenever source and target executions are both defined,
    their complete observations are equal

over the declared finite corpus.

It is not yet the stronger proof obligation:

    Gamma_r |- lhs(r) == rhs(r)

The purpose of the next N4 phase is to derive explicit sufficient
premises Gamma_r instead of relying on a posteriori exclusions.


## 8. DOMAIN definedness census

A complete definedness census over the existing R0 corpus partitioned
DOMAIN-rule executions into:

    DD = source defined,  target defined
    DO = source defined,  target overflow
    OD = source overflow, target defined
    OO = source overflow, target overflow

Results:

    total cases: 1,151,400

    DD: 1,113,405
    DO:     1,455
    OD:     1,432
    OO:    35,108

Defined/defined observation mismatches:

    0

The census exactly reconstructs the earlier R0 counters:

    OD + OO = 36,540 source exclusions
    DO      =  1,455 target escapes

This demonstrates that DOMAIN is not a single homogeneous semantic
category.

Some rules can introduce overflow relative to their source program,
while others can remove overflow.


## 9. Candidate runtime-rule promotions

Five current DOMAIN helpers showed no definedness asymmetry in the
initial census:

    _cap_shift_before_zero_reset_from_compare_bound
    _pull_saturated_acc_across_compare
    _normalize_temporal_cmp2_barrier
    _normalize_temporal_guarded_reset_commute
    _normalize_temporal_shift_width

They were subjected to an expanded promotion stress search using:

    all 256 possible initial raw states
    112 stress SpikeTrains

Total concrete cases:

    12,730,368

For every candidate:

    DO = 0
    OD = 0
    observation mismatches = 0

Promotion search:

    supported candidates: 5
    refuted candidates:    0

These five rules are NOT reclassified by this checkpoint.

The result is finite empirical evidence supporting promotion from
DOMAIN to RUNTIME. Reclassification requires a local algebraic proof
or an appropriately exhaustive proof over the declared formal domain.


## 10. Emerging DOMAIN taxonomy

The definedness census suggests at least three operational classes:

    D+ : rewrites capable of introducing overflow
    D- : rewrites capable of removing overflow
    D0 : no definedness asymmetry observed

The five promotion candidates currently belong empirically to D0.

This taxonomy is diagnostic only and is not yet part of the formal
RuleValidity API.


## 11. Foundational operational principle

Overflow is observable behavior.

Therefore:

    dead final value != dead execution

A rewrite cannot be classified as runtime-safe merely because a changed
intermediate state is later overwritten or annihilated.

Intermediate execution effects, including overflow, belong to the
observable operational semantics.


## 12. Epistemic boundary

This checkpoint does not claim universal completeness of the full SPK
Core rewrite system.

The validated claims are restricted to the explicitly declared finite
program corpora, configurations and stress domains used by the
corresponding experiments, except where an individual law already has
a separate algebraic proof.

In particular:

- the 7380-program runtime quotient is a finite checkpoint;
- R0 is finite evidence with explicit DOMAIN exclusions;
- the five promotion candidates have strong finite evidence but have
  not yet been formally promoted;
- explicit executable Gamma_r premises remain future work.


## 13. Next phase

The next N4 step is local proof analysis of the five promotion
candidates.

For each candidate the required obligations are:

    Obs(lhs) = Obs(rhs)

and:

    Overflow(lhs) iff Overflow(rhs)

under the declared Core semantics.

Candidates that satisfy these obligations algebraically may be
reclassified from D to L.

For the remaining genuinely domain-dependent rules, the next objective
is to derive explicit sufficient premises:

    Gamma_r

and eventually require:

    Gamma_r |- lhs(r) == rhs(r)

before a DOMAIN rewrite is permitted operationally.
