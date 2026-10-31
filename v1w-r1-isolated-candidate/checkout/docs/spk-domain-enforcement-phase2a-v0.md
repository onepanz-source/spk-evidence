# SPK Algebra v0 — DOMAIN enforcement Phase 2a

## Status

Phase 2a introduces fail-closed enforcement for DOMAIN rewrites.

Base checkpoint:

    5aad861 checkpoint: close N4 runtime promotion candidates

## Motivation

Historically, CanonicalizationProfile.FULL caused DOMAIN rules to execute
without executable evidence that their declared premise Gamma_r held.

The RUNTIME profile disabled DOMAIN rules, but the normal canonicalization
entry points did not.

Therefore DOMAIN was a classification and documentation mechanism, not an
enforced semantic contract.

## Phase 2a invariant

Normal canonicalization is now fail-closed:

    no explicit DOMAIN capability
        => no DOMAIN rewrite

The temporary context manager:

    unchecked_domain_rules()

may explicitly enable DOMAIN implementations.

It is intentionally named "unchecked": activation is not evidence that any
Gamma_r premise is satisfied.

Its permitted uses in Phase 2a are limited to:

- tests whose purpose is to exercise a DOMAIN rewrite;
- finite DOMAIN definedness/soundness harnesses;
- finite candidate stress searches.

Runtime canonicalization remains unable to activate DOMAIN rules even inside
an unchecked DOMAIN scope.

## Remaining DOMAIN rules

Core:

- D-ACC-03
- D-RESET-01
- D-TIME-05
- D-ZERO-01

Semantic:

- D-ACC-01
- D-COUNT-01
- D-TIME-01
- D-ZERO-02

## Definedness census

For the eight remaining DOMAIN rules:

    changed programs: 2588
    cases: 983440

    DD: 956021
    DO:   1455
    OD:   1432
    OO:  24532

    DD observation mismatches: 0

The reconstructed aggregate exclusions agree with the rule-soundness gate:

    source exclusions: 25964
    target escapes:     1455

The census is required to be non-vacuous. A run with zero changed programs
or zero concrete cases is an error and cannot produce PASS.

## Candidate finite stress

The historical five promotion candidates remain available to the finite
stress harness.

The harness now reports:

    FINITE STRESS SUPPORTED
    FINITE STRESS REFUTED
    NOT EXERCISED

A candidate with zero changed programs or zero cases cannot be classified as
supported.

"FINITE STRESS SUPPORTED" is evidence over the declared finite stress corpus.
It is not a universal proof and does not imply promotion from DOMAIN to
RUNTIME.

In particular D-TIME-01 remains DOMAIN despite finite stress support because
its applicability depends on abstract-analysis evidence.

## Soundness gate

Current finite rule-soundness result:

    rewrite helpers checked: 29
    changed source programs: 42222
    concrete observation cases: 16044360
    source overflow cases observed: 579049
    matched runtime overflow cases: 553085
    runtime source-overflow removals: 0
    runtime target-overflow failures: 0
    declared domain source exclusions: 25964
    declared domain target escapes: 1455
    observation mismatches: 0

Result:

    PASS WITH DECLARED DOMAIN EXCLUSIONS

## What Phase 2a does not prove

Phase 2a does not yet provide executable Gamma_r evidence.

unchecked_domain_rules() is a temporary research capability, not a production
proof mechanism.

The next Phase 2 work is to replace unchecked activation with explicit
DomainEvidence / Gamma_r predicates for each remaining DOMAIN rule.

## Roadmap checkpoint

Progress percentages are conservative engineering estimates against explicit
acceptance criteria, not mathematical proof percentages.

| Phase | Progress | Change from 5aad861 | Next requirement |
|---|---:|---:|---|
| 1. Close five D->L candidates | 100% | 0 pp | complete |
| 2. Formalize and enforce Gamma_r | 35% | +15 pp | executable DomainEvidence |
| 3. NF stability / termination / idempotence / ambiguity | 70% | 0 pp | rerun after Gamma enforcement |
| 4. Consolidate and freeze reproducible Core v0 | 55% | +5 pp | integrate final DOMAIN contract |
| 5. Minimal simulated-network extensions | 20% | 0 pp | remains separate from Core freeze |

Equal-weight total:

    56%

Phase 5 remains deliberately separate from Core v0 closure.
