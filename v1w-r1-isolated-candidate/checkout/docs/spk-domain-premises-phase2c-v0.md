# SPK Domain Premises — Phase 2c v0

## Scope

This checkpoint closes the premise classification for all eight current
DOMAIN rewrite rules.

It does not yet provide production DomainEvidence.

DOMAIN rewrites remain fail-closed by default. Historical proof/search
harnesses may enable them explicitly through `unchecked_domain_rules()`.

## Result

All current DOMAIN rules now have an explicit locally justified premise
class.

| Premise class | Rules |
|---|---:|
| SOURCE_DEFINED | 5 |
| TARGET_DEFINED | 1 |
| BOTH_DEFINED | 1 |
| ABSTRACT_BOUND | 1 |
| Unresolved | 0 |

Total DOMAIN rules: 8.

## SOURCE_DEFINED

Rules:

- D-ACC-03
- D-ZERO-01
- D-COUNT-01
- D-ACC-01
- D-ZERO-02

Local obligation:

    Def(source) => Def(target)

and:

    Def(source) => Obs(source) == Obs(target)

The five rules have local hand proofs and independent finite regression.

## TARGET_DEFINED

Rule:

- D-TIME-05

Local obligation:

    Def(target) => Def(source)

and:

    Def(target) => Obs(source) == Obs(target)

The rewrite removes pre-ACC shifts after CMP(1).  Removing those shifts
can increase target raw state and therefore introduce target overflow.

The reverse definedness implication is locally proved by raw-state
dominance.

Finite regression independently exercises DO witnesses and no OD cases.

## BOTH_DEFINED

Rule:

- D-RESET-01

Local obligation:

    Def(source) and Def(target)
        => Obs(source) == Obs(target)

Neither unilateral definedness premise is sufficient.

A DO witness exists in the finite census.

An independent OD witness is:

    CMP(1); RESET(255); ACC(1,c); RESET(0)

with initial raw 1 and one event on c.

The source overflows after RESET(255); ACC(+1), while the target remains
defined.

Therefore neither:

    Def(source) => Def(target)

nor:

    Def(target) => Def(source)

holds in general.

## ABSTRACT_BOUND

Rule:

- D-TIME-01

The matcher uses conservative abstract-state bounds produced by
`analyze_program()`.

The abstract invariant is:

    concrete reachable raw states of defined executions
        subseteq
    abstract RawSet

This is not a proof of execution definedness.

### Abstract transfer soundness

- `RawSet.top()` contains every valid unsigned raw value.
- `CoreAcc` conservatively represents every defined result of adding an
  arbitrary nonnegative count multiple.
- `ShiftDecay` conservatively maps to `[0, upper]` when delta is unknown.
- `CoreCmp` conservatively partitions raw state by the threshold.
- `CoreEmit` preserves raw state and guard.
- `CoreReset` sets the true branch to the exact reset value.
- `join_raw()` conservatively contains the union of both branches.

Therefore, by induction over program instructions, abstract upper bounds
contain every concrete raw state reached by a defined execution.

### D-TIME-01 consequence

If:

    merged.upper <= 1

then every concrete reachable raw value is in `{0,1}`.

For raw values in `{0,1}`, `ShiftDecay(k)` for every positive k has the
same behavior as `ShiftDecay(1)`:

- delta == 0: identity;
- delta > 0: result is zero.

The second matcher case requires only the FALSE branch to satisfy
`upper <= 1`.  On the TRUE branch only `CoreEmit` may occur before a
guaranteed `RESET(0)`.

`CoreAcc` is deliberately forbidden in this interval because changing
the shift width could alter observable overflow before the reset.

## Important distinction

Abstract soundness means:

    every concrete state produced by a defined execution is represented
    by the abstraction.

It does not mean:

    the abstraction proves that every possible execution is defined.

Overflow remains observable.

## Current DOMAIN taxonomy

    5 SOURCE_DEFINED
    1 TARGET_DEFINED
    1 BOTH_DEFINED
    1 ABSTRACT_BOUND

No current DOMAIN rule has an unresolved premise.

## Enforcement status

The premise semantics are now understood, but production enforcement is
not complete.

Current behavior remains:

    default canonicalization -> DOMAIN disabled
    runtime profile          -> DOMAIN disabled
    unchecked_domain_rules   -> explicit proof/test bypass only

The next Phase 2 activity is to design typed `DomainEvidence` that can
authorize DOMAIN rewrites only when the corresponding premise has been
established.

`unchecked_domain_rules()` must not become a production evidence path.

## Roadmap checkpoint

| Phase | Progress |
|---|---:|
| 1. D -> L candidate closure | 100% |
| 2. DOMAIN premises and enforcement | 75% |
| 3. NF stability / termination / idempotence / ambiguity | 70% |
| 4. Core v0 consolidation and freeze | 55% |
| 5. Minimal simulated-network extensions | 20% |

Equal-weight total:

    (100 + 75 + 70 + 55 + 20) / 5 = 64%

Phase 2 increased from 50% to 75%.

The remaining Phase 2 work is production evidence representation,
validation, propagation and removal of unchecked DOMAIN authorization
from non-proof paths.
