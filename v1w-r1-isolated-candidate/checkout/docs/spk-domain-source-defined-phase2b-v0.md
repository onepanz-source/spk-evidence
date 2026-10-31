# SPK Algebra v0 — DOMAIN SOURCE_DEFINED closure

## Status

This checkpoint follows:

    3f18500 checkpoint: make DOMAIN rewrites fail closed

It closes the SOURCE_DEFINED premise family for the current eight
remaining DOMAIN rules.

## Meaning of SOURCE_DEFINED

For a DOMAIN rewrite

    source -> target

SOURCE_DEFINED means that the local proof establishes:

    Def(source) => Def(target)

and, over the matched rewrite pattern:

    Def(source) => Obs(source) == Obs(target)

Therefore target definedness does not need to be an independent
premise for these rules.

The rule remains DOMAIN because the converse need not hold:

    Overflow(source) and Def(target)

is possible and is observable under the current Core semantics.

## Closed rules

Five DOMAIN rules now have status:

    SOURCE_DEFINED / PROVED_LOCAL

They are:

- D-ACC-01
- D-ACC-03
- D-COUNT-01
- D-ZERO-01
- D-ZERO-02

No SOURCE_DEFINED_CANDIDATE remains.

## Local proof mechanisms

### D-ACC-01

Positive ACC weight reduction before CMP(1)/RESET(0).

The target ACC contribution is no greater than the source contribution.

Mechanism:

    monotone raw-state dominance

### D-ACC-03

A saturating ACC weight is reduced to the minimum weight sufficient for
the following guarded reset pattern.

The target raw state is no greater than the source raw state.

Mechanism:

    monotone raw-state dominance

### D-COUNT-01

Pattern:

    ACC(w,c);
    SHIFT(k);
    ACC(v,c);
    CMP(1);
    RESET(r)

Both ACC instructions see the same batch count n_c and SHIFT sees the
same delta.

Removing the first ACC cannot increase target raw state, and the second
positive ACC makes the CMP(1) branch identical whenever n_c > 0.
For n_c == 0 both programs reduce to the same shifted state.

Mechanism:

    shared-count identity plus monotonicity

### D-ZERO-01

Pattern:

    X;
    CMP(1);
    RESET(0);
    CMP(1)

where X is ACC, SHIFT or RESET.

The suffix maps every defined unsigned raw state to:

    raw   = 0
    guard = False

Mechanism:

    complete state/guard annihilator

### D-ZERO-02

A contiguous ACC/SHIFT state prefix precedes:

    CMP(1);
    RESET(0)

The zero barrier annihilates the raw state.

The guard created by CMP(1) is required to be overwritten by a later
CMP before any EMIT or RESET can consume it.

Mechanism:

    zero barrier plus dead guard

## Independent finite regression

Aggregate finite census for the five SOURCE_DEFINED rules:

    rules:              5
    changed programs: 174
    cases:          66120

    DD:             64492
    DO:                 0
    OD:              1432
    OO:               196

    DD observation mismatches: 0

All 1432 OD cases in the current eight-rule DOMAIN census belong to
this SOURCE_DEFINED family.

The finite regression is not the mathematical proof. It is an
independent implementation regression against the local hand proofs.

## Remaining DOMAIN premise classes

After this checkpoint:

    SOURCE_DEFINED:         5
    SOURCE_DEFINED_CANDIDATE: 0
    TARGET_DEFINED_REQUIRED: 2
    ABSTRACT_BOUND:          1

Remaining rules:

    D-TIME-05   TARGET_DEFINED_REQUIRED
    D-RESET-01  TARGET_DEFINED_REQUIRED
    D-TIME-01   ABSTRACT_BOUND

D-TIME-05 and D-RESET-01 have concrete DO witnesses, therefore:

    Def(source) does not imply Def(target)

for those rules.

D-TIME-01 instead depends on abstract reachable-state bounds and must
be treated separately.

## What this checkpoint does not yet provide

SOURCE_DEFINED is currently a proved premise classification, not yet a
production DomainEvidence capability.

Normal canonicalization remains fail-closed.

The temporary unchecked_domain_rules() capability remains restricted to
tests and proof/search harnesses.

A later phase will connect proved premises to executable DomainEvidence.

## Roadmap checkpoint

Percentages are conservative engineering estimates against explicit
acceptance criteria, not mathematical proof percentages.

| Phase | Progress | Change from 3f18500 | Remaining work |
|---|---:|---:|---|
| 1. Close five D->L candidates | 100% | 0 pp | complete |
| 2. Formalize and enforce Gamma_r | 50% | +15 pp | 2 target-defined rules, abstract-bound proof, DomainEvidence |
| 3. NF stability / termination / idempotence / ambiguity | 70% | 0 pp | rerun after final DOMAIN enforcement |
| 4. Consolidate and freeze reproducible Core v0 | 55% | 0 pp | integrate final DOMAIN contract |
| 5. Minimal simulated-network extensions | 20% | 0 pp | remains separate from Core freeze |

Equal-weight total:

    59%

Phase 5 remains deliberately separate from Core v0 closure.
